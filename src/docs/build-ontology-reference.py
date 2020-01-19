#!/usr/bin/env python

# Copyright 2010-2011 Sebastian Trueg <trueg@kde.org>
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from PyQt4 import QtCore
from PyKDE4 import soprano
import sys
import codecs
import glob


# our tree, maps URIs to EntityContainer objects
entityTree = {}

# the namespaces mapped to their abbreviation, the label, and the description
# using a map with keys "abbr", "label", and "desc"
allNamespaces = {}


def normalizeUri(uri):
  ns = uri.left(uri.lastIndexOf(QtCore.QRegExp('[#/]'))+1)
  name = uri.mid(uri.lastIndexOf(QtCore.QRegExp('[#/]'))+1)
  if ns in allNamespaces:
    return '%s:%s' % (allNamespaces[ns]['abbr'], name)
  elif ns == soprano.Soprano.Vocabulary.RDF.rdfNamespace().toString():
    return 'rdf:%s' % name
  elif ns == soprano.Soprano.Vocabulary.RDFS.rdfsNamespace().toString():
    return 'rdfs:%s' % name
  elif ns == soprano.Soprano.Vocabulary.XMLSchema.xsdNamespace().toString():
    return 'xsd:%s' % name
  else:
    return uri


def elidedText(s, maxLen):
    if s.length() <= maxLen:
        return s
    else:
        return s.left(maxLen) + "..."


def resolveAbbreviatedUri(abbrevUri):
  abbr = abbrevUri.left(abbrevUri.indexOf(':'))
  name = abbrevUri.mid(abbr.length()+1)
  for ns in allNamespaces.keys():
    if abbr == allNamespaces[ns]['abbr']:
      return ns + name
  return ''


def buildDocBookEntity(entityUri):
  if entityUri in entityTree:
    return entityTree[entityUri].createDocBookLink()
  else:
    return normalizeUri(entityUri)

      
def buildDocBookEntityList(entityUris, directRelations = ()):
  s = QtCore.QStringList()
  for uri in entityUris:
    link = buildDocBookEntity(uri)
    if uri in directRelations:
      link = link + ' (direct)'
    s.append(link)
  return s.join(', ')


def buildXRefList(linkends):
  s = QtCore.QStringList()
  for link in linkends:
    s.append('<xref linkend="%s" />' % link)
  return s.join(', ')


class EntityContainer(object):
  """
  A container for a class or a property with members
  for uri, label, comment, and lists with sub and super
  entities. The lists contain all sub and super entities,
  not only the direct ones.
  """
  
  def comment(self):
    return self.m_comment
    
  def label(self):
    return self.label
    
  def uri(self):
    return self.uri
    
  def name(self):
    return self.uri.mid(self.uri.lastIndexOf(QtCore.QRegExp('[#/]'))+1)

  def namespace(self):
    return self.uri.left(self.uri.lastIndexOf(QtCore.QRegExp('[#/]'))+1)

  def parents(self):
    return self.parents
    
  def children(self):
    return self.children
    
  def buildSuperEntityHash(self, subRelations):
    if len(self.superEntities) == 0:
      self.directSuperEntities = subRelations.get(self.uri, [])
      for type in subRelations.get(self.uri, []):
        if not type in self.superEntities:
          self.superEntities.add(type)
          self.superEntities |= entityTree[type].buildSuperEntityHash(subRelations)
    # just to be sure
    self.superEntities.discard(self.uri)
    return self.superEntities
  
  def buildSubEntityHash(self, superRelations):
    if len(self.subEntities) == 0:
      self.directSubEntities = superRelations.get(self.uri, [])
      for type in superRelations.get(self.uri, []):
        if not type in self.subEntities:
          self.subEntities.add(type)
          self.subEntities |= entityTree[type].buildSubEntityHash(superRelations)
    self.subEntities.discard(self.uri)
    return self.subEntities

  def createDocBookLink(self):
      # For external entities (like geo) we do not have any details
      if self.namespace() in allNamespaces:
          entityId = "%s:%s" % (allNamespaces[self.namespace()]["abbr"], self.name())
          return '<link linkend="%s">%s</link>' % (entityId, entityId)
      else:
          return '<ulink url="%s">%s</ulink>' % (self.uri, self.uri)



  def toDocBook(self):
    entityId = "%s:%s" % (allNamespaces[self.namespace()]["abbr"], self.name())
    s = '<section id="%s"><title>' % entityId
    s += entityId
    if self.deprecated:
      s += ' <emphasis>(deprecated)</emphasis>'
    s += '</title><informaltable>'
    s += '<tgroup cols="2"><tbody>'
    s += '<row><entry align="right">Label</entry><entry>%s</entry></row>' % self.label
    s += '<row><entry align="right">Description</entry><entry><![CDATA[%s]]></entry></row>' % self.comment()
    if self.isProperty:
      s += '<row><entry align="right">Domain</entry><entry>%s</entry></row>' % buildDocBookEntity(self.domain)
      s += '<row><entry align="right">Range</entry><entry>%s</entry></row>' % buildDocBookEntity(self.range)
      if self.minCardinality != -1:
        s += '<row><entry align="right">Minimum Cardinality</entry><entry>%i</entry></row>' % self.minCardinality
      if self.cardinality != -1:
        s += '<row><entry align="right">Cardinality</entry><entry>%i</entry></row>' % self.cardinality
      if self.maxCardinality != -1:
        s += '<row><entry align="right">Maximum Cardinality</entry><entry>%i</entry></row>' % self.maxCardinality
      if self.minCardinality == -1 and self.cardinality == -1 and self.maxCardinality == -1:
        s += '<row><entry align="right">Cardinality</entry><entry><emphasis>none</emphasis></entry></row>'
      s += '<row><entry align="right">Super-properties</entry><entry>%s</entry></row>' % buildDocBookEntityList(self.superEntities, self.directSuperEntities)
      s += '<row><entry align="right">Sub-properties</entry><entry>%s</entry></row>' % buildDocBookEntityList(self.subEntities, self.directSubEntities)
      if not self.inverseProperty.isEmpty():
        s += '<row><entry align="right">Inverse Property</entry><entry>%s</entry></row>' % buildDocBookEntity(self.inverseProperty)
    else:
      s += '<row><entry align="right">Super-classes</entry><entry>%s</entry></row>' % buildDocBookEntityList(self.superEntities, self.directSuperEntities)
      s += '<row><entry align="right">Sub-classes</entry><entry>%s</entry></row>' % buildDocBookEntityList(self.subEntities, self.directSubEntities)
      s += '<row><entry align="right">In domain of</entry><entry>%s</entry></row>' % buildDocBookEntityList(self.inDomainOf)
      s += '<row><entry align="right">In range of</entry><entry>%s</entry></row>' % buildDocBookEntityList(self.inRangeOf)
      if len(self.instances) > 0:
        s += '<row><entry align="right">Instances</entry><entry>%s</entry></row>' % buildDocBookEntityList(self.instances)
    if len(self.backlinks) > 0:
      s += '<row><entry align="right">Mentioned in</entry><entry>%s</entry></row>' % buildXRefList(self.backlinks)
    s += '</tbody></tgroup></informaltable></section>'
    return s

  def toShortDocBook(self):
      entityId = "%s:%s" % (allNamespaces[self.namespace()]["abbr"], self.name())
      return '<xref linkend="%s"/> - %s' % (entityId, elidedText(self.comment(), 80))

  def __init__(self, uri):
    self.uri = uri
    self.superEntities = set()
    self.subEntities = set()
    self.directSuperEntities = set()
    self.directSubEntities = set()
    self.isProperty = False
    self.inDomainOf = set()
    self.inRangeOf = set()
    self.instances = set()
    self.domain = QtCore.QString()
    self.range = QtCore.QString()
    self.cardinality = -1
    self.minCardinality = -1
    self.maxCardinality = -1
    self.m_comment = QtCore.QString()
    self.inverseProperty = QtCore.QString();
    self.backlinks = set()
    self.deprecated = False

  def __cmp__(self, other):
    if self.name() < other.name(): return -1
    if self.name() > other.name(): return 1
    else: return 0
    

def buildEntityTree(ontologyFiles):
  "Build a tree of all classes and properties with full hierarchy"

  graph = soprano.Soprano.Graph()
  parser = soprano.Soprano.PluginManager.instance().discoverParserForSerialization(soprano.Soprano.SerializationTrig)
  for f in ontologyFiles:
    it = parser.parseFile(f, QtCore.QUrl(), soprano.Soprano.SerializationTrig)
    while it.next():
      graph.addStatement(it.current())
  
  # get all classes and properties
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.RDF.type()), soprano.Soprano.Node())
  while(it.next()):
    if it.current().object().uri() != soprano.Soprano.Vocabulary.RDF.Property() and it.current().object().uri() != soprano.Soprano.Vocabulary.RDFS.Class():
      continue
    uri = it.current().subject().uri().toString()
    if not uri in entityTree:
      entityTree[uri] = EntityContainer(uri)
      entityTree[uri].isProperty = (it.current().object().uri() == soprano.Soprano.Vocabulary.RDF.Property())
      
  # add labels and comments
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.RDFS.label()), soprano.Soprano.Node())
  while(it.next()):
    uri = it.current().subject().uri().toString()
    if uri in entityTree:
      entityTree[uri].label = it.current().object().toString()
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.RDFS.comment()), soprano.Soprano.Node())
  while(it.next()):
    uri = it.current().subject().uri().toString()
    if uri in entityTree:
      entityTree[uri].m_comment = it.current().object().toString()

  # mark deprecated classes and properties
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.NAO.deprecated()), soprano.Soprano.Node())
  while(it.next()):
    uri = it.current().subject().uri().toString()
    if uri in entityTree:
      entityTree[uri].deprecated = it.current().object().literal().toBool()

  # add hierarchy
  subRelations = {}
  superRelations = {}
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.RDFS.subClassOf()), soprano.Soprano.Node())
  while(it.next()):
    child = it.current().subject().uri().toString()
    parent = it.current().object().uri().toString()
    if child in entityTree and parent in entityTree:
      subRelations.setdefault(child, []).append(parent)
      superRelations.setdefault(parent, []).append(child)
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.RDFS.subPropertyOf()), soprano.Soprano.Node())
  while(it.next()):
    child = it.current().subject().uri().toString()
    parent = it.current().object().uri().toString()
    if child in entityTree and parent in entityTree:
      subRelations.setdefault(child, []).append(parent)
      superRelations.setdefault(parent, []).append(child)
  for e in entityTree.values():
    e.buildSuperEntityHash(subRelations)
    e.buildSubEntityHash(superRelations)
    
  # save ranges and domains
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.RDFS.domain()), soprano.Soprano.Node())
  while(it.next()):
    prop = it.current().subject().uri().toString()
    domain = it.current().object().uri().toString()
    if prop in entityTree:
      entityTree[prop].domain = domain
    if domain in entityTree:
      entityTree[domain].inDomainOf.add(prop)
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.RDFS.range()), soprano.Soprano.Node())
  while(it.next()):
    prop = it.current().subject().uri().toString()
    range = it.current().object().uri().toString()
    if prop in entityTree:
      entityTree[prop].range = range
    if range in entityTree:
      entityTree[range].inRangeOf.add(prop)

  # save instances
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.RDF.type()), soprano.Soprano.Node())
  while(it.next()):
    type = it.current().object().uri().toString()
    if type in entityTree:
      entityTree[type].instances.add(it.current().subject().uri().toString())

  # save cardinalities
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.NRL.minCardinality()), soprano.Soprano.Node())
  while(it.next()):
    prop = it.current().subject().uri().toString()
    c = it.current().object().literal().toInt()
    if prop in entityTree:
      entityTree[prop].minCardinality = c
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.NRL.maxCardinality()), soprano.Soprano.Node())
  while(it.next()):
    prop = it.current().subject().uri().toString()
    c = it.current().object().literal().toInt()
    if prop in entityTree:
      entityTree[prop].maxCardinality = c
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.NRL.cardinality()), soprano.Soprano.Node())
  while(it.next()):
    prop = it.current().subject().uri().toString()
    c = it.current().object().literal().toInt()
    if prop in entityTree:
      entityTree[prop].cardinality = c

  # save inverse properties
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.NRL.inverseProperty()), soprano.Soprano.Node())
  while(it.next()):
    p1 = it.current().subject().uri().toString()
    p2 = it.current().object().uri().toString()
    if p1 in entityTree:
      entityTree[p1].inverseProperty = p2

  # extract namespace abbreviations
  it = graph.listStatements(soprano.Soprano.Node(), soprano.Soprano.Node(soprano.Soprano.Vocabulary.NAO.hasDefaultNamespaceAbbreviation()), soprano.Soprano.Node())
  while(it.next()):
    s = it.current().subject().uri().toString()
    abbrev = it.current().object().toString()
    allNamespaces.setdefault(s, {})["abbr"] = abbrev
    
  # extract namespace labels and descriptions
  for ns in allNamespaces.keys():
    it = graph.listStatements(soprano.Soprano.Node(QtCore.QUrl(ns)), soprano.Soprano.Node(soprano.Soprano.Vocabulary.NAO.prefLabel()), soprano.Soprano.Node())
    if(it.next()):
      allNamespaces.setdefault(ns, {})["label"] = it.current().object().literal().toString()
    it = graph.listStatements(soprano.Soprano.Node(QtCore.QUrl(ns)), soprano.Soprano.Node(soprano.Soprano.Vocabulary.NAO.description()), soprano.Soprano.Node())
    if(it.next()):
      allNamespaces.setdefault(ns, {})["desc"] = it.current().object().literal().toString()


def extractEntityBacklinks(docbookFolder):
  "Extracts links from documentation to classes and properties. The backlinks are stored in the entityTree as string ids to be used in xref docbook links."
  # Parse each docbook file and find xref links which relate to a class or a property
  # for each xref find the containing section and store its id in the entity's backlinks list
  for filename in glob.glob(docbookFolder + '/*-main.docbook'):
    #
    # We need a well-formed docbook document for the stream reader.
    # Thus we fake one by putting the file contents into an article
    #
    file = QtCore.QFile(filename)
    file.open(QtCore.QIODevice.ReadOnly)
    content = file.readAll()
    content.prepend('<article>')
    content.append('</article>')

    xml = QtCore.QXmlStreamReader(content)
    sectionStack = []
    while not xml.atEnd():
      tokenType = xml.readNext()
      if tokenType == QtCore.QXmlStreamReader.StartElement:
        if xml.name() == 'section':
          if xml.attributes().hasAttribute('id'):
            sectionStack.append(xml.attributes().value('id').toString())
        elif xml.name() == 'xref':
          linkend = xml.attributes().value('linkend').toString()
          resolvedUri = resolveAbbreviatedUri(linkend)
          if resolvedUri in entityTree:
            entityTree[resolvedUri].backlinks.add(sectionStack[-1])
      elif tokenType == QtCore.QXmlStreamReader.EndElement:
        if xml.name() == 'section':
          sectionStack.pop()


def printEntityTree():
  for e in entityTree.values():
    print "%s (%s) (%s)" % (e.label, e.uri, e.isProperty)
    print "   Name:         %s" % e.name()
    print "   Parents:      %s" % e.superEntities
    print "   Children:     %s" % e.subEntities
    if e.isProperty:
      print "   Domain:       %s" % e.domain
      print "   Range:        %s" % e.range
      print "   Min card:     %i" % e.minCardinality
      print "   Max card:     %i" % e.maxCardinality
    else:
      print "   In domain of: %s" % e.inDomainOf
      print "   In range of:  %s" % e.inRangeOf
    print ""
    
    
def getSortedClasses(ns = ''):
  classes = []
  for a in entityTree.values():
    if not a.isProperty and (len(ns) == 0 or a.namespace() == ns):
      classes.append(a)
  classes.sort()
  return classes


def getSortedProperties(ns = ''):
  properties = []
  for a in entityTree.values():
    if a.isProperty and (len(ns) == 0 or a.namespace() == ns):
      properties.append(a)
  properties.sort()
  return properties

  
def writeDocBookAppendix(ns):
  "Writes a file <NS-ABBREV>-reference.docbook to the current folder."
  name = allNamespaces[ns]["abbr"]
  filename = '%s-reference.docbook' % name
  f = codecs.open(filename, 'w', 'utf-8')
  f.write('<section xmlns="http://docbook.org/ns/docbook"><title>%s Vocabulary Summary</title>' % name.toUpper())

  sortedClasses = getSortedClasses(ns)
  if len(sortedClasses) > 0:
      f.write('<section><title>Description of Classes</title>')
      for a in sortedClasses:
          f.write(a.toDocBook())
      f.write('</section>')

  sortedProperties = getSortedProperties(ns)
  if len(sortedProperties) > 0:
      f.write('<section><title>Description of Properties</title>')
      for a in sortedProperties:
          f.write(a.toDocBook())
      f.write('</section>')
  f.write('</section>')


def writeMainOntologyFile(ns):
    "Writes the main ontology docbook file which includes all the others based on the template."
    name = allNamespaces[ns]["abbr"]
    title = '%s - %s' % (name.toUpper(), allNamespaces[ns]["label"])
    abstract = allNamespaces[ns]["desc"]

    filename = '%s.docbook' % name
    f = open(filename, 'w')
    template = open('ontology.docbook.template', 'r')
    for line in template:
        line = line.replace('%NAMESPACE%', ns)
        line = line.replace('%TITLE%', title)
        line = line.replace('%ABSTRACT%', abstract)
        line = line.replace('%ABBREV%', name)
        f.write(line + '\n')
    f.close()


def writeOntologyOverviewFile(ns):
    "Writes a file containing a list of all entities as an overview"
    name = allNamespaces[ns]["abbr"]
    filename = '%s-overview.docbook' % name
    f = open(filename, 'w')

    sortedClasses = getSortedClasses(ns)
    if len(sortedClasses) > 0:
        f.write('<section xmlns="http://docbook.org/ns/docbook">')
        f.write('<title>Classes Overview</title>')
        f.write('<informaltable><tgroup cols="1"><tbody>')
        for a in sortedClasses:
            f.write('<row><entry>%s</entry></row>' % a.toShortDocBook())
        f.write('</tbody></tgroup></informaltable>')
        f.write('</section>')

    sortedProperties = getSortedProperties(ns)
    if len(sortedProperties) > 0:
        f.write('<section xmlns="http://docbook.org/ns/docbook">')
        f.write('<title>Properties Overview</title>')
        f.write('<informaltable><tgroup cols="1"><tbody>')
        for a in getSortedProperties(ns):
            f.write('<row><entry>%s</entry></row>' % a.toShortDocBook())
        f.write('</tbody></tgroup></informaltable>')
        f.write('</section>')

def writeOntologyToc():
    "Writes a TOC file which lists links to all ontologies"
    f = open('ontotoc.docbook', 'w')
    f.write('<itemizedlist xmlns="http://docbook.org/ns/docbook">')
    for ns in allNamespaces.keys():
        f.write('<listitem><para><xref linkend="%s"/></para>' % allNamespaces[ns]["abbr"])
        f.write('<para>%s</para></listitem>' % allNamespaces[ns]["desc"])
    f.write('</itemizedlist>')
    f.close()


def writeClassIndex():
    "Writes one docbook file containing an index of all classes"
    f = open('classindex.docbook', 'w')
    f.write('<chapter id="classindex" xmlns="http://docbook.org/ns/docbook">')
    f.write('<title>All Classes</title>')
    currentChar = ''
    for a in getSortedClasses():
        if not a.namespace() in allNamespaces:
            continue
        if currentChar != a.name()[0]:
            if len(currentChar) > 0:
                f.write('</tbody></tgroup></informaltable></section>')
            currentChar = a.name()[0]
            f.write('<section><title>%s</title>' % currentChar.toUpper())
            f.write('<informaltable><tgroup cols="1"><tbody>')
        f.write('<row><entry>%s</entry></row>' % a.toShortDocBook())
    f.write('</tbody></tgroup></informaltable></section>')
    f.write('</chapter>')
    f.close()


def writePropertyIndex():
    "Writes one docbook file containing an index of all properties"
    f = open('propertyindex.docbook', 'w')
    f.write('<chapter id="propertyindex" xmlns="http://docbook.org/ns/docbook">')
    f.write('<title>All Properties</title>')
    currentChar = ''
    for a in getSortedProperties():
        if not a.namespace() in allNamespaces:
            continue
        if currentChar != a.name()[0]:
            if len(currentChar) > 0:
                f.write('</tbody></tgroup></informaltable></section>')
            currentChar = a.name()[0]
            f.write('<section><title>%s</title>' % currentChar.toUpper())
            f.write('<informaltable><tgroup cols="1"><tbody>')
        f.write('<row><entry>%s</entry></row>' % a.toShortDocBook())
    f.write('</tbody></tgroup></informaltable></section>')
    f.write('</chapter>')
    f.close()


def main():
  buildEntityTree(sys.argv[2:])
  extractEntityBacklinks(sys.argv[1])
  # write an index of all classes
  writeClassIndex()
  writePropertyIndex()
  # Write the separate ontology doc files
  for ns in allNamespaces.keys():
    writeDocBookAppendix(ns)
    writeOntologyOverviewFile(ns)
    writeMainOntologyFile(ns)
  # Write the list of ontologies for the title page
  writeOntologyToc()


if __name__ == "__main__":
    main()
