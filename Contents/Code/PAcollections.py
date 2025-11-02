import PAutils


class PhoenixCollections:
    collectionsTable = []

    def addCollection(self, newCollection):
        newCollection = newCollection.encode('UTF-8') if isinstance(newCollection, unicode) else newCollection
        if newCollection.lower() not in map(str.lower, self.collectionsTable):
            self.collectionsTable.append(newCollection)

    def clearCollections(self):
        self.collectionsTable = []

    def processCollections(self, metadata, siteNum):
        for collectionLink in self.collectionsTable:
            collectionName = collectionLink.replace('"', '').replace('\xc2\xa0', ' ').strip()

            metadata.collections.add(collectionName)
