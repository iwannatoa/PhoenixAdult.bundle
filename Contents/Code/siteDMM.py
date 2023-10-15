import PAsearchSites
import PAutils
import operator

cookies = {
    'age_check_done': '1',
}


def search(results, lang, siteNum, searchData):
    searchJAVID = None
    splitSearchTitle = searchData.title.split()
    if len(splitSearchTitle) > 1:
        if unicode(splitSearchTitle[1], 'UTF-8').isdigit():
            searchJAVID = '%s%%20%s' % (splitSearchTitle[0], splitSearchTitle[1])
            directJAVID = ('%s%5s' % (splitSearchTitle[0], splitSearchTitle[1])).replace(' ', '0')

    if searchJAVID:
        searchData.encoded = searchJAVID

        sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded

        req = PAutils.HTTPRequest(sceneURL, cookies=cookies)
        searchResults = HTML.ElementFromString(req.text)
        for searchResult in searchResults.xpath('//div[@class="d-sect"]//ul[@class="list-large"]/li'):
            titleNoFormatting = searchResult.xpath('.//span[@class="txt"]')[0].text_content().replace('\t', '').replace('\r\n', '').strip()
            sceneURL = searchResult.xpath('.//p[@class="tmb"]/a/@href')[0].rsplit('/', 1)[0]
            fJAVID = sceneURL.rsplit('cid=', 1)[1].replace('/', '').strip()
            JAVID = '%s-%s' % (fJAVID[0:-5], int(fJAVID[-5:]))
            curID = PAutils.Encode(sceneURL)

            if searchJAVID:
                score = 100 - Util.LevenshteinDistance(searchJAVID.lower(), JAVID.lower())
            else:
                score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, JAVID), name='[%s] %s' % (JAVID, titleNoFormatting), score=score, lang=lang))

    if directJAVID:
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + '/digital/videoa/-/detail/=/cid=' + directJAVID
        req = PAutils.HTTPRequest(sceneURL, cookies=cookies)
        searchResult = HTML.ElementFromString(req.text)
        errSign = searchResult.xpath('//span[@class="d-txten"]')
        if not errSign or not operator.contains(errSign[0].text_content(), '404'):
            javTitle = searchResult.xpath('//h1[@id="title"]')[0].text_content().strip()
            JAVID = '%s-%s' % (directJAVID[0:-5], int(directJAVID[-5:]))
            curID = PAutils.Encode(sceneURL)
            score = 100
            results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, JAVID), name='[Direct][%s] %s' % (JAVID, javTitle), score=score, lang=lang))
    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    JAVID = metadata_id[2]

    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    req = PAutils.HTTPRequest(sceneURL, cookies=cookies)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    javTitle = detailsPageElements.xpath('//div[@class="hreview"]/h1')[0].text_content().strip()
    javTitle = JAVID + ' ' + javTitle
    metadata.title = javTitle

    # Studio
    javStudio = ''
    studio = detailsPageElements.xpath('//td/a[contains(@href, "maker")]')
    if studio:
        javStudio = studio[0].text_content().strip()
    metadata.studio = javStudio

    #  Tagline and Collection(s)
    data = {}

    label = detailsPageElements.xpath('//td/a[contains(@href, "label")]')
    if label:
        data['Label'] = label[0].text_content().strip()

    series = detailsPageElements.xpath('//td/a[contains(@href, "series")]')
    if series:
        data['Series'] = series[0].text_content().strip()

    metadata.tagline = ', '.join(['%s: %s' % (key, value) for key, value in data.items()])
    if label:
        metadata.tagline = label[0].text_content().strip()
        metadata.collections.add(metadata.tagline)
    else:
        metadata.collections.add(metadata.studio)
    # Release Date
    dateOrigin = detailsPageElements.xpath('//td[@class="nw"]/../../tr[3]/td[2]')
    # date = dateOrigin[dateOrigin.find(':')+2:]
    if dateOrigin:
        date = dateOrigin[0].text_content().replace('\n', '').strip()
        date_object = datetime.strptime(date, '%Y/%m/%d')
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    for genreLink in detailsPageElements.xpath('//td/a[contains(@href, "keyword")]'):
        genreName = genreLink.text_content().lower().strip()
        movieGenres.addGenre(genreName)

    # Actor(s)
    actors = detailsPageElements.xpath('//td/span/a[contains(@href, "actress")]')
    for actorsLink in actors:
        fullActorName = actorsLink.text_content()
        actorPhotoURL = ''
        movieActors.addActor(fullActorName, actorPhotoURL)

    # for actorLink in actors:
    #     fullActorName = actorLink.xpath('.//span[@class="ttl"]')[0].text_content()
    #     actorPhotoURL = actorLink.xpath('.//span[@class="img"]/img/@src')[0]
    #     Log('%s actorPhotoURL: %s' % (fullActorName, actorPhotoURL))
    #     if not actorPhotoURL.startswith('http'):
    #         actorPhotoURL = PAsearchSites.getSearchBaseURL(siteNum) + actorPhotoURL
    #     actorPhoto = PAutils.HTTPRequest(actorPhotoURL)
    #     if not actorPhoto.ok or actorPhotoURL.rsplit('/', 1)[1] == 'nowprinting.jpg':
    #         actorPhotoURL = ''
    #
    #     movieActors.addActor(fullActorName, actorPhotoURL)

    # Posters
    xpaths = [
        '//div[@id="sample-video"]/a/img/@src',
        '//div[@id="sample-video"]/a/@href',
        '//div[@id="sample-image-block"]/a/@href',
    ]
    for xpath in xpaths:
        for poster in detailsPageElements.xpath(xpath):
            if not poster.startswith('http'):
                poster = PAsearchSites.getSearchBaseURL(siteNum) + poster
            art.append(poster)

    images = []
    posterExists = False
    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                images.append(image)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if height > width:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                    posterExists = True
                if width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    if not posterExists:
        for idx, image in enumerate(images, 1):
            try:
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[art[idx - 1]] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
