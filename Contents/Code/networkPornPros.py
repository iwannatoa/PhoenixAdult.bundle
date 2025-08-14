import PAsearchSites
import PAutils


def getDataFromAPI(siteNum, searchType, slug, site, searchSite):
    headers = {'x-site': site}

    url = '%s/%s/%s' % (searchSite, searchType, slug)

    req = PAutils.HTTPRequest(url, headers=headers)

    data = None
    if req.ok:
        data = req.json()
    
    if not data and siteNum == 1693 and 'momcum' not in searchSite:
        data = getDataFromAPI(siteNum, searchType, slug, site.replace('pornplus', 'momcum'), searchSite.replace('pornplus', 'momcum'))
    if not data and '-' in slug and '--' not in slug:
        data = getDataFromAPI(siteNum, 'releases', PAutils.rreplace(slug, '-', '--', 1), site, searchSite)

    return data


def search(results, lang, siteNum, searchData):
    searchData.encoded = slugify(searchData.title.lower().replace('\'', '').replace('.', ''))

    searchResult = getDataFromAPI(siteNum, 'releases', searchData.encoded, PAsearchSites.getSearchBaseURL(siteNum), PAsearchSites.getSearchSearchURL(siteNum))

    titleNoFormatting = PAutils.parseTitle(searchResult['title'], siteNum)
    subSite = searchResult['sponsor']['name']
    curID = PAutils.Encode(searchData.encoded)

    date = searchResult['releasedAt']
    if date:
        releaseDate = parse(date).strftime('%Y-%m-%d')
    else:
        releaseDate = searchData.dateFormat() if searchData.date else ''
    displayDate = releaseDate if date else ''

    if searchData.date and displayDate:
        score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
    else:
        score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

    results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, subSite, displayDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    metadata_id = str(metadata.id).split('|')
    slug = PAutils.Decode(metadata_id[0])
    sceneDate = metadata_id[2]

    detailsPageElements = getDataFromAPI(siteNum, 'releases', slug, PAsearchSites.getSearchBaseURL(siteNum), PAsearchSites.getSearchSearchURL(siteNum))

    # Title
    metadata.title = PAutils.parseTitle(str(detailsPageElements['title']), siteNum)

    # Summary
    summary = str(detailsPageElements['description'].strip())
    if summary.lower() != 'n/a':
        metadata.summary = summary

    # Studio
    metadata.studio = 'PornPros'

    # Tagline and Collection(s)
    tagline = str(detailsPageElements['sponsor']['name'])
    metadata.tagline = tagline
    metadata.collections.add(metadata.tagline)

    # Release Date
    date = detailsPageElements['releasedAt']
    if date:
        date_object = parse(date)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year
    elif sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    junkTags = [str(actorName['name']).replace(' ', '').lower() for actorName in detailsPageElements['actors']]
    junkTags.append(tagline.replace(' ', '').lower())
    genres = detailsPageElements['tags'] + PAutils.getDictValuesFromKey(genresDB, PAsearchSites.getSearchSiteName(siteNum).replace(' ', '').lower())
    for genreLink in genres:
        genreName = genreLink.replace('_', ' ').replace('-', ' ').strip()

        if '.' in genreName and 'st.' not in genreName:
            for genreLink in genreName.split('.'):
                genreName = genreLink.strip()
                if genreName.replace(' ', '').lower() not in junkTags:
                    movieGenres.addGenre(genreName)
        else:
            if genreName.replace(' ', '').lower() not in junkTags:
                movieGenres.addGenre(genreName)

    # Actor(s)
    for actorLink in detailsPageElements['actors']:
        actorName = actorLink['name']
        actorPhotoURL = ''

        modelPageElements = getDataFromAPI(siteNum, 'actors', actorLink['cached_slug'], PAsearchSites.getSearchBaseURL(siteNum), PAsearchSites.getSearchSearchURL(siteNum))
        if modelPageElements:
            actorPhotoURL = modelPageElements['thumbUrl'].split('?')[0]

        if '&' in actorName:
            for actor in actorName.split('&'):
                movieActors.addActor(actor.strip(), '')
        else:
            movieActors.addActor(actorName, actorPhotoURL)

    # Manually Add Actors
    # Add Actor Based on Title
    for actor in PAutils.getDictValuesFromKey(actorsDB, metadata.title):
        movieActors.addActor(actor, '')

    # Posters
    art.append(detailsPageElements['posterUrl'].split('?')[0])

    if detailsPageElements['thumbUrls']:
        thumbUrl = detailsPageElements['thumbUrls'][0].rsplit('/', 1)[0]
    elif detailsPageElements['thumbUrl']:
        thumbUrl = detailsPageElements['thumbUrl'].rsplit('/', 1)[0]

    if 'handtouched' in thumbUrl:
        for idx in range(1, 20):
            art.append('%s/%03d.jpg' % (thumbUrl, idx))
    else:
        if detailsPageElements['thumbUrls']:
            art.extend([x.split('?')[0] for x in detailsPageElements['thumbUrls']])
        elif detailsPageElements['thumbUrl']:
            art.append(detailsPageElements['thumbUrl'].split('?')[0])

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
    'anal4k': ['Anal', 'Ass', 'Creampie'],
    'bbcpie': ['Interracial', 'BBC', 'Creampie'],
    'cum4k': ['Creampie'],
    'deepthroatlove': ['Blowjob', 'Deep Throat'],
    'girlcum': ['Orgasms', 'Girl Orgasm', 'Multiple Orgasms'],
    'holed': ['Anal', 'Ass'],
    'lubed': ['Lube', 'Raw', 'Wet'],
    'massagecreep': ['Massage', 'Oil'],
    'passion-hd': ['Hardcore'],
    'povd': ['Gonzo', 'POV'],
    'puremature': ['MILF', 'Mature'],
}

actorsDB = {
    'Poke Her In The Front': ['Sara Luvv', 'Dillion Harper'],
    'Best Friends With Nice Tits!': ['April O\'Neil', 'Victoria Rae Black'],
}

