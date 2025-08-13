import PAsearchSites
import PAutils


def getDataFromAPI(siteNum, searchType, slug):
    headers = {'x-site': PAsearchSites.getSearchBaseURL(siteNum)}

    url = '%s/%s/%s' % (PAsearchSites.getSearchSearchURL(siteNum), searchType, slug)

    req = PAutils.HTTPRequest(url, headers=headers)

    data = None
    if req.ok:
        data = req.json()

    return data


def search(results, lang, siteNum, searchData):
    searchData.encoded = slugify(searchData.title.lower())
    searchResult = getDataFromAPI(siteNum, 'releases', searchData.encoded)

    titleNoFormatting = PAutils.parseTitle(searchResult['title'], siteNum)
    subSite = searchResult['sponsor']['name']
    curID = PAutils.Encode(searchData.encoded)
    releaseDate = searchData.dateFormat() if searchData.date else ''

    score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

    results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s]' % (titleNoFormatting, subSite), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    slug = PAutils.Decode(metadata_id[0])
    sceneDate = metadata_id[2]

    detailsPageElements = getDataFromAPI(siteNum, 'releases', slug)

    # Title
    metadata.title = PAutils.parseTitle(detailsPageElements['title'], siteNum)

    # Summary
    metadata.summary = detailsPageElements['description']

    # Studio
    metadata.studio = 'PornPros'

    # Actor(s)
    for actorLink in detailsPageElements['actors']:
        actorName = actorLink['name']
        actorPhotoURL = ''

        modelPageElements = getDataFromAPI(siteNum, 'actors', actorLink['cached_slug'])
        if modelPageElements:
            actorPhotoURL = modelPageElements['thumbUrl'].split('?')[0]

        movieActors.addActor(actorName, actorPhotoURL)

    # Tagline and Collection(s)
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    metadata.collections.add(metadata.tagline)

    # Manually Add Actors
    # Add Actor Based on Title
    for actor in PAutils.getDictValuesFromKey(actorsDB, metadata.title):
        movieActors.addActor(actor, '')

    # Release Date
    if sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    genres = PAutils.getDictValuesFromKey(genresDB, PAsearchSites.getSearchSiteName(siteNum))
    genres.extend(detailsPageElements['tags'])
    for genreLink in genres:
        genreName = genreLink.strip()

        movieGenres.addGenre(genreName)

    # Posters
    art.append(detailsPageElements['posterUrl'].split('?')[0])

    thumbUrl = detailsPageElements['thumbUrls'][0].rsplit('/', 1)[0]

    if 'handtouched' in thumbUrl:
        for idx in range(1, 20):
            art.append('%s/%03d.jpg' % (thumbUrl, idx))
    else:
        art.extend([x.split('?')[0] for x in detailsPageElements['thumbUrls']])

    images = []
    imgHQcount = 0
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
                if width >= 850:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                    imgHQcount += 1
                if width >= 850:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                break

    # Add Low Res images to posters if only 1 HQ image found
    if not imgHQcount > 1:
        for idx, image in enumerate(images, 1):
            try:
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[art[idx + (imgHQcount - 1)]] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata


genresDB = {
    'Anal4K': ['Anal', 'Ass', 'Creampie'],
    'BBCPie': ['Interracial', 'BBC', 'Creampie'],
    'Cum4K': ['Creampie'],
    'DeepThroatLove': ['Blowjob', 'Deep Throat'],
    'GirlCum': ['Orgasms', 'Girl Orgasm', 'Multiple Orgasms'],
    'Holed': ['Anal', 'Ass'],
    'Lubed': ['Lube', 'Raw', 'Wet'],
    'MassageCreep': ['Massage', 'Oil'],
    'PassionHD': ['Hardcore'],
    'POVD': ['Gonzo', 'POV'],
    'PureMature': ['MILF', 'Mature'],
}

actorsDB = {
    'Poke Her In The Front': ['Sara Luvv', 'Dillion Harper'],
    'Best Friends With Nice Tits!': ['April O\'Neil', 'Victoria Rae Black'],
}
