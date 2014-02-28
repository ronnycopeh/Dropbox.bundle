import simplejson, urllib, urllib2, os
json = simplejson

# Static text. 
APP_NAME = 'Dropbox'
LOGO = 'logo.png'

# Image resources.
ICON_FOLDER = R('folder.png')
ICON_PLAY = R('play.png')
ICON_SEARCH = R('search.png')
ICON_PREFERENCES = R('preferences.png')

# Other definitions.
PLUGIN_PREFIX = '/video/dropbox'
debug = True
debug_raw = True

####################################################################################################

def Start():
	Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, APP_NAME, LOGO)
	Plugin.AddViewGroup("List", viewMode = "List", mediaType = "items")
	Plugin.AddViewGroup("InfoList", viewMode = "InfoList", mediaType = "items")

####################################################################################################

@handler('/video/dropbox', APP_NAME, art = R('logo.png'))
def MainMenu():
	oc = ObjectContainer(no_cache = True, view_group = 'List', art = 'logo.png')

	if checkConfig():
		if debug == True: Log('Configuration check: OK!')

		oc = getDropboxStructure()

		# Add preferences.
		oc.add(InputDirectoryObject(key=Callback(searchDropbox), title = 'Crawl your dropbox', prompt = 'Search for', thumb = ICON_SEARCH))
		oc.add(PrefsObject(title = L('preferences')))
	else:
		if debug == True: Log('Configuration check: FAILED!')
		oc.title1 = None
		oc.header = L('error')
                oc.message = L('error_no_config')
		oc.add(PrefsObject(title = L('preferences'), thumb = ICON_PREFERENCES))

	return oc

####################################################################################################

def ValidatePrefs():
	if debug == True: Log("Validating preferences")
	mode = Prefs['access_mode'].lower()
	tmp = apiRequest("https://api.dropbox.com/1/metadata/" + mode + '/')
	if tmp != False:
		if debug == True: Log("Testcall to api finished with success. Preferences valid")
		Dict['PrefsValidated'] = True;
	else:
		if debug == True: Log("Testcall to api failed. Preferences invalid")
		Dict['PrefsValidated'] = False;
	return True

####################################################################################################

def checkConfig():
	if 'PrefsValidated' in Dict and Dict['PrefsValidated'] == True:
		return True
	else:
		return False

####################################################################################################

def getFilenameFromPath(path):
	filepath, fileext = os.path.splitext(path)
	fileext = fileext.lower()
	filepatharray = filepath.split('/')
	return [filepatharray[len(filepatharray)-1], fileext]

####################################################################################################

def apiRequest(call):
	if debug == True: Log("apiRequest() - talking to dropbox api: " + call)

        headers = { "Authorization" : "Bearer " + Prefs['access_token']
        }
	try:
	        req = urllib2.Request(call, None, headers)
	        response = urllib2.urlopen(req)
	        result = response.read()
	except Exception, e:
		if debug == True: Log("ERROR! apiRequest(): " + str(e))
		return False
        return result

####################################################################################################

def getDropboxMetadata(path, search = False, query = ''):
	mode = Prefs['access_mode'].lower() 
	call = ''
	if search == False:
		call = "https://api.dropbox.com/1/metadata/" + mode + path
	else:
		call = "https://api.dropbox.com/1/search/" + mode + path + "?" + query 
	if debug == True: Log("getDropboxMetadata() url call: " + call)

	tmp = apiRequest(call)
	if tmp != False:
		try:
			json_data = json.loads(tmp)
		except Exception, e:
			if debug == True: Log("ERROR! getDropboxMetadata(): " + str(e))
			return False
		return json_data
	else:
		return False

####################################################################################################

def getDropboxLinkForFile(path):
	mode = Prefs['access_mode'].lower()
	tmp = apiRequest("https://api.dropbox.com/1/media/" + mode + path)
	if tmp != False:
		try:
			json_data = json.loads(tmp)
			if debug_raw == True: Log("Got link data for: " + path)
			if debug_raw == True: Log(json_data)
		except Exception, e:
			if debug == True: Log("ERROR! getDropboxMetadata(): " + str(e))
			return False
		return json_data
	else:
		return False

####################################################################################################

def createContentObjectList(metadata):
	objlist = []
	# Loop through the content.
	for item in metadata:
		# Check wether it's a folder or file.
		if item['is_dir'] == True:
			if debug == True: Log("Adding folder '" + item['path'])
			foldernamearray = item['path'].split('/')
			foldername = foldernamearray[len(foldernamearray)-1]
			objlist.append(DirectoryObject(key=Callback(getDropboxStructure, path=item['path']), title=foldername, thumb=ICON_FOLDER))
		else:
			if debug == True: Log("Evaluating item '" + item['path'])
			obj = createMediaObject(item)
			if obj != False:
				objlist.append(obj)
	return objlist

def getDropboxStructure(path = '/'):
	oc = ObjectContainer(no_cache = True, view_group = 'List', art = R('logo.png'))
	if debug == True: Log("Called getDropboxStructure(" + path + ")")

	metadata = getDropboxMetadata(path)
	if metadata == False:
		oc.title1 = None
		oc.header = L('error')
		oc.message = L('error_webrequest_failed')
		return oc 

	if debug_raw == True: Log("Got metadata for folder: " + path)
	if debug_raw == True: Log(metadata)

	objlist = createContentObjectList(metadata['contents'])
	for obj in objlist:
		oc.add(obj)

	return oc

####################################################################################################

def searchDropbox(query):
	oc = ObjectContainer(no_cache = True, view_group = 'List', art = R('logo.png'))
        if debug == True: Log("Crawling dropbox for: " + query)

	urlquery = {'query' : query }
	metadata = getDropboxMetadata('/', True, urllib.urlencode(urlquery))
	if metadata == False:
		oc.title1 = None
		oc.header = L('error')
		oc.message = L('error_webrequest_failed')
		return oc

	if debug_raw == True: Log("Got metadata for query: " + query)
	if debug_raw == True: Log(metadata)

	objlist = createContentObjectList(metadata)
	for obj in objlist:
		oc.add(obj)

	if len(objlist) == 0:
		
		return ObjectContainer(header = L('text_search_result'), message = L('text_no_search_results_for') + " \"" + query + "\"")
        return oc

####################################################################################################

def createMediaObject(item):
	if debug == True: Log("Checking item: " + item['path'])
	filename, fileext = getFilenameFromPath(item['path']) 

	# Handle movie files.
	if fileext == '.mp4' or fileext == '.mkv' or fileext == '.avi' or fileext == '.mov':
		urldata = getDropboxLinkForFile(item['path'])
		if urldata == False:
			return False
		return createVideoClipObject(item, urldata['url'])
	return False

####################################################################################################

def createVideoClipObject(item, url, container = False):
	if debug == True: Log("Creating VideoClipObject for item: " + item['path'])
	filename, fileext = getFilenameFromPath(item['path'])

	summary = "Size: " + item['size'] + "\n"
	if container:
		summary = summary + "Path: " + item['path'] + "\n"
		summary = summary + "Modified: " +  item['modified'] + "\n"

	vco = VideoClipObject(
		key = Callback(createVideoClipObject, item = item, url = url, container = True),
		rating_key = url,
		title = filename + fileext,
		summary = summary, 
		thumb = ICON_PLAY,
		items = []
	)
	mo = MediaObject(parts = [PartObject(key = url)])

	# Guess the video container type.
	if fileext == ".mp4":
		mo.container = Container.MP4
	elif fileext == ".mkv":
		mo.container = Container.MKV
	elif fileext == ".avi":
		mo.container = Container.AVI
	else:
		mo.container = Container.MOV

	# Append mediaobject to clipobject.
	vco.items.append(mo)

	if container:
		return ObjectContainer(objects = [vco])
	else:
		return vco
	return vco