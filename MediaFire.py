#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Autor: ehooo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import urlparse, httplib, urllib, hashlib, json, datetime, os

class MediaFireBase:
	MEDIAFIRE_URL =  "%(protocol)s://www.mediafire.com/api/%(path)s/%(function)s.php"

	def __init__(self, path, response_format = 'json', version=2.9):
		if not response_format in ['json', 'xml']:
			raise Exception('response_format only support json or xml')
		assert isinstance(version, float)
		assert isinstance(path, str) or isinstance(path, unicode)

		self.response_format = response_format
		self.version = version
		self.path = path

	def toUTF8(self,s):
		"""Convert unicode to utf-8."""
		if isinstance(s, unicode):
			return s.encode("utf-8")
		else:
			return unicode(str(s),"utf-8").encode("utf-8")

	def _send_data(self, function, data={}, headers={}, post=None, protocol='https'):
		url = MediaFireBase.MEDIAFIRE_URL % {'protocol':protocol, 'path':self.path,'function':function}

		headers.update({"Accept": "*/*"})
		if not 'Content-Type' in headers:
			headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
		if not 'User-Agent' in headers:
			headers["User-Agent"] = "ehooo's MediaFire Python API Wrapper"

		data['response_format'] = self.response_format
		data['version'] = self.version
		get = ""
		if post is None:
			post = [(k, self.toUTF8(v)) for k, v in data.items()]
			post = urllib.urlencode(post)
		else:
			get = [(k, self.toUTF8(v)) for k, v in data.items()]
			get = urllib.urlencode(get)
			get = '?'+get

		parseUrl = urlparse.urlparse(url)
		host = parseUrl.netloc
		if parseUrl.hostname:
			host = parseUrl.hostname
		if parseUrl.port:
			host += ":"+parseUrl.port

		conn = None
		if parseUrl.port == 443 or parseUrl.scheme == 'https':
			conn = httplib.HTTPSConnection(host)
		else:
			conn = httplib.HTTPConnection(host)

		conn.request("POST",parseUrl.path + get, post, headers)
		response = conn.getresponse()
		ret = response.read()
		if response.status != httplib.OK:
			if response.status == httplib.FORBIDDEN:
				self._proccess_response(ret)
			head = response.getheaders()
			conn.close()
			raise IOError(response.status, ret, head)
		conn.close()
		return self._proccess_response(ret)

	def _proccess_response(self, response):
		if self.response_format == 'json':
			response = json.loads(response)
			if response['response']['result'].lower() != "success":
				raise RuntimeError(response['response']['error'], response['response']['message'])
			return response['response']
		else:
			#TODO --PROCCESS ERRORS
			return response

class MediaFireUser(MediaFireBase):
	SESSION_TIME_LIVE = 10*60
	def __init__(self, application_id, API_Key, renew_gap=3*60):
		MediaFireBase.__init__(self, 'user')
		self.__session_token = None
		self.__expired_time = 0
		self._application_id = application_id
		self._API_Key = API_Key
		self.renew_gap = renew_gap

	def session_token(self):
		if self.__expired_time:
			delta = datetime.datetime.utcnow() - self.__expired_time
			if delta.total_seconds() >= self.renew_gap + MediaFireUser.SESSION_TIME_LIVE:
				self.renew_session_token()
		return self.__session_token

	def _get_signature(self, email, password):
		hash_ = hashlib.sha1()
		hash_.update(email)
		hash_.update(password)
		hash_.update(self._application_id)
		hash_.update(self._API_Key)
		return hash_.hexdigest()

	def get_session_token(self, email, password):
		data = {
			'email': email,
			'password':password,
			'application_id': self._application_id,
			'signature':self._get_signature(email, password)
		}
		response = self._send_data('get_session_token',data)
		self.__expired_time = datetime.datetime.utcnow()
		self.__session_token = response['session_token']

	def renew_session_token(self):
		data = { 'session_token': self.__session_token }
		self._send_data('renew_session_token',data)
		self.__expired_time = datetime.datetime.utcnow()

	def get_login_token(self, email, password):
		data = {
			'email': email,
			'password':password,
			'application_id': self._application_id,
			'signature':self._get_signature(email, password)
		}
		response = self._send_data('get_login_token',data)
		return response['login_token']

	def register(self, email, password, display_name=None, first_name=None, last_name=None):
		data = {
			'email': email,
			'password':password,
			'application_id': self._application_id
		}
		if display_name:
			data['display_name'] = display_name
		if first_name:
			data['first_name'] = first_name
		if last_name:
			data['last_name'] = last_name

		self._send_data('register',data)

	def get_info(self):
		data = { 'session_token': self.__session_token }
		return self._send_data('get_info',data)['user_info']

	def update(self, display_name=None, first_name=None, last_name=None, birth_date=None, gender=None, website=None, location=None, newsletter=None, primary_usage=None):
		data = { 'session_token': self.__session_token }
		if display_name:
			assert isinstance(display_name, str) or isinstance(display_name, unicode)
			data['display_name'] = display_name
		if first_name:
			assert isinstance(first_name, str) or isinstance(first_name, unicode)
			data['first_name'] = first_name
		if last_name:
			assert isinstance(last_name, str) or isinstance(last_name, unicode)
			data['last_name'] = last_name
		if birth_date:
			if isinstance(birth_date, datetime.date) or isinstance(birth_date, datetime.datetime):
				birth_date = birth_date.strftime("%Y/%m/%d")
			assert isinstance(birth_date, str) or isinstance(birth_date, unicode)
			data['birth_date'] = birth_date
		if gender:
			if gender in ['male', 'female', 'none']:
				data['gender'] = gender
			else:
				data['gender'] = 'none'
		if website:
			assert isinstance(website, str) or isinstance(website, unicode)
			data['website'] = website
		if location:
			assert isinstance(location, str) or isinstance(location, unicode)
			data['location'] = location

		if newsletter is not None:
			if newsletter:
				data['newsletter'] = 'yes'
			else:
				data['newsletter'] = 'no'
		if primary_usage:
			if primary_usage in ['home', 'work', 'school', 'none'] :
				data['primary_usage'] = primary_usage
			else:
				data['primary_usage'] = 'none'

		self._send_data('update',data)

	def myfiles_revision(self):
		data = { 'session_token': self.__session_token }
		return self._send_data('myfiles_revision',data)

class MediaFireFile(MediaFireBase):
	def __init__(self, quick_key, user=None):
		MediaFireBase.__init__(self, 'file')
		if user:
			assert isinstance(user, MediaFireUser)
			self.user = user
		else:
			self.user = None
		if isinstance(quick_key, list):
			quick_key = ",".join(quick_key)
		assert isinstance(quick_key, str) or isinstance(quick_key, unicode)
		self.quick_key = quick_key
	def get_info(self):
		data = {'quick_key':self.quick_key}
		if self.user and self.user.session_token():
			data['session_token'] = self.user.session_token()
		return self._send_data('get_info',data)['file_info']

	def delete(self):
		data = {
			'quick_key':self.quick_key,
			'session_token': self.user.session_token()
		}
		self._send_data('delete',data)
		self.quick_key = None

	def move(self, folder_key=None):
		data = {
			'quick_key':self.quick_key,
			'session_token': self.user.session_token()
		}
		if folder_key:
			data['folder_key'] = folder_key
		self._send_data('move',data)

	def update(self, filename=None,description=None,tags=[],privacy=None,note_subject=None,note_description=None):
		data = {
			'quick_key':self.quick_key,
			'session_token': self.user.session_token()
		}
		if filename:
			assert isinstance(filename, str) or isinstance(filename, unicode)
			data['filename'] = filename
		if description:
			assert isinstance(description, str) or isinstance(description, unicode)
			data['description'] = description
		if len(tags) > 0:
			data['tags'] = ','.join(tags)
		if privacy:
			if privacy in ['public' or 'private']:
				data['privacy'] = privacy
		if note_subject:
			assert isinstance(note_subject, str) or isinstance(note_subject, unicode)
			data['note_subject'] = note_subject
		if note_description:
			assert isinstance(note_description, str) or isinstance(note_description, unicode)
			data['note_description'] = note_description
		self._send_data('update',data)

	def update_password(self, password):
		data = {
			'quick_key':self.quick_key,
			'session_token': self.user.session_token(),
			'password':password
		}
		self._send_data('update_password',data)

	def update_file(self, to_quickkey):
		if isinstance(to_quickkey, list):
			to_quickkey = ",".join(to_quickkey)
		assert isinstance(to_quickkey, str) or isinstance(to_quickkey, unicode)
		data = {
			'from_quickkey':self.quick_key,
			'to_quickkey':to_quickkey,
			'session_token': self.user.session_token()
		}
		self._send_data('update_file',data)
		self.quick_key = to_quickkey

	def copy(self, folder_key=None):
		data = {
			'quick_key':self.quick_key,
			'session_token': self.user.session_token()
		}
		if folder_key:
			data['folder_key'] = folder_key
		self._send_data('copy',data)

	def get_links(self, link_type=None):
		data = {
			'quick_key':self.quick_key
		}
		if self.user and self.user.session_token():
			data['session_token'] = self.user.session_token()
		if link_type in ['view', 'edit', 'normal_download', 'direct_download', 'one_time_download']:
			data['link_type'] = link_type
		return self._send_data('get_links',data)

	def collaborate(self, quick_key=None,emails=None,duration=None,message=None,public=None):
		data = { 'session_token': self.user.session_token() }
		if quick_key:
			data['quick_key'] = self.quick_key
		if emails:
			assert isinstance(emails, str) or isinstance(emails, unicode)
			data['emails'] = emails
		if duration:
			assert isinstance(duration, int)
			data['duration'] = duration
		if message:
			assert isinstance(message, str) or isinstance(message, unicode)
			data['message'] = message
		if public is not None:
			if public:
				if public in ['yes', 'no']:
					data['public'] = public
				else:
					data['public'] = 'yes'
			else:
				data['public'] = 'no'
		self._send_data('collaborate',collaborate)

class MediaFireFolder(MediaFireBase):
	def __init__(self, folder_key=None, user=None):
		MediaFireBase.__init__(self, 'folder')
		if user:
			assert isinstance(user, MediaFireUser)
			self.user = user
		else:
			self.user = None
		if folder_key:
			if isinstance(folder_key, list):
				folder_key = ",".join(folder_key)
			assert isinstance(folder_key, str) or isinstance(folder_key, unicode)
			self.folder_key = folder_key
		else:
			self.folder_key = None

	def get_info(self):
		data = {}
		if self.folder_key:
			data['folder_key'] = self.folder_key
		if self.user and self.user.session_token():
			data['session_token'] = self.user.session_token()
		return self._send_data('get_info',data)['folder_info']

	def delete(self):
		data = {
			'folder_key':self.folder_key,
			'session_token': self.user.session_token()
		}
		self._send_data('delete',data)
		self.folder_key = None
	def move(self, folder_key_dst=None):
		data = {
			'folder_key_src':self.folder_key,
			'session_token': self.user.session_token()
		}
		if folder_key_dst:
			data['folder_key_dst'] = folder_key_dst
		self._send_data('move',data)
	def create(self, foldername, parent_key=None):
		assert isinstance(foldername, str) or isinstance(foldername, unicode)
		data = {
			'foldername':foldername,
			'session_token': self.user.session_token()
		}
		if parent_key:
			if isinstance(parent_key, MediaFireFolder):
				parent_key = parent_key.folder_key
			else:
				assert isinstance(parent_key, str) or isinstance(parent_key, unicode)
			data['parent_key'] = parent_key
		response = self._send_data('create',data)
		return response['folder_key'], response['upload_key']

	def update(self, foldername=None,description=None,tags=[],privacy=None,privacy_recursive=None,note_subject=None,note_description=None):
		data = {
			'folder_key':self.folder_key,
			'session_token': self.user.session_token()
		}
		if foldername:
			assert isinstance(foldername, str) or isinstance(foldername, unicode)
			data['foldername'] = foldername
		if description:
			assert isinstance(description, str) or isinstance(description, unicode)
			data['description'] = description
		if len(tags) > 0:
			data['tags'] = ','.join(tags)
		if privacy:
			if privacy in ['public' or 'private']:
				data['privacy'] = privacy
		if privacy_recursive is not None:
			if privacy_recursive:
				if privacy_recursive in ['yes', 'no']:
					data['privacy_recursive'] = privacy_recursive
				else:
					data['privacy_recursive'] = 'yes'
			else:
				data['privacy_recursive'] = 'no'
		if note_subject:
			assert isinstance(note_subject, str) or isinstance(note_subject, unicode)
			data['note_subject'] = note_subject
		if note_description:
			assert isinstance(note_description, str) or isinstance(note_description, unicode)
			data['note_description'] = note_description
		self._send_data('update',data)

	def attach_foreign(self):
		data = {
			'folder_key':self.folder_key,
			'session_token': self.user.session_token()
		}
		self._send_data('attach_foreign',data)

	def detach_foreign(self):
		data = {
			'folder_key':self.folder_key,
			'session_token': self.user.session_token()
		}
		self._send_data('detach_foreign',data)

	def get_revision(self):
		data = { 'folder_key':self.folder_key}
		return self._send_data('get_revision',data)

	def get_depth(self):
		data = {
			'folder_key':self.folder_key,
			'session_token': self.user.session_token()
		}
		return self._send_data('get_depth',data)

	def get_siblings(self, content_filter=None,start=None, limit=None):
		data = {
			'folder_key':self.folder_key
		}
		if self.user and self.user.session_token():
			data['session_token'] = self.user.session_token()
		if content_filter in ['info', 'files', 'folders', 'content', 'all']:
			data['content_filter'] = content_filter
		if start:
			assert isinstance(start, int)
			data['start'] = start
		if limit:
			assert isinstance(limit, int)
			data['limit'] = limit
		return self._send_data('get_siblings',data)

	def search(self, search_text):
		assert isinstance(search_text, str) or isinstance(search_text, unicode)
		data = {'search_text':search_text}
		if self.folder_key:
			data['folder_key'] = self.folder_key
		if self.user and self.user.session_token():
			data['session_token'] = self.user.session_token()
		return self._send_data('search',data)

	def get_content(self, content_type=None, order_by=None, order_direction=None, chunk=None):
		data = {}
		if self.folder_key:
			data['folder_key'] = self.folder_key
		if self.user and self.user.session_token():
			data['session_token'] = self.user.session_token()

		if content_type in ['folders','files']:
			data['content_type'] = content_type
		if order_by in ['name', 'created', 'size', 'downloads']:
			data['order_by'] = order_by
		if order_direction in ['asc', 'desc']:
			data['order_direction'] = order_direction
		if chunk:
			assert isinstance(chunk, int)
			if chunk<1:
				raise ValueError('chunk must be greater than 1')
			data['chunk'] = chunk

		return self._send_data('get_content',data,protocol='http')['folder_content']

class MediaFireUpload(MediaFireBase):
	def __init__(self, user=None):
		MediaFireBase.__init__(self, 'upload')
		if user:
			assert isinstance(user, MediaFireUser)
			self.user = user
		else:
			self.user = None

	def upload(self, file_upload, uploadkey=None, dropbox=None):
		data = {}
		if uploadkey:
			assert isinstance(uploadkey, str) or isinstance(uploadkey, unicode)
			data['uploadkey'] = uploadkey
		if dropbox:
			data['dropbox'] = 1
			assert isinstance(uploadkey, str) or isinstance(uploadkey, unicode)
			data['uploadkey'] = uploadkey
		else:
			data['session_token'] = self.user.session_token()

		headers={
			'x-filename' : os.path.basename(file_upload),
			'x-filesize': os.path.getsize(file_upload),
            'Content-Type' : 'application/octet-stream'
		}
		with open(file_upload, 'rb') as f:
			cont = f.read()
			f.close()
			return self._send_data('upload', data, headers, cont, 'http')
		raise IOError("File couldn't be opened "+str(file_upload))

	def poll_upload(self, key):
		data = {
			'key':key,
			'session_token':self.user.session_token()
		}
		return self._send_data('poll_upload', data)

class MediaFireSystem(MediaFireBase):
	def __init__(self):
		MediaFireBase.__init__(self, 'system')

	def get_version(self):
		return self._send_data('get_version')['current_api_version']

	def get_info(self):
		return self._send_data('get_info')

	def get_supported_media(self, group_by_filetype=None):
		data = {}
		if group_by_filetype is not None:
			if group_by_filetype:
				if group_by_filetype in ['yes','no']:
					data['group_by_filetype'] = group_by_filetype
				else:
					data['group_by_filetype'] = 'yes'
			else:
				data['group_by_filetype'] = 'no'
		return self._send_data('get_supported_media', data)['viewable']

	def get_editable_media(self):
		data = {}
		if group_by_filetype is not None:
			if group_by_filetype:
				if group_by_filetype in ['yes','no']:
					data['group_by_filetype'] = group_by_filetype
				else:
					data['group_by_filetype'] = 'yes'
			else:
				data['group_by_filetype'] = 'no'
		return self._send_data('get_editable_media', data)['editable']
	def get_mime_types(self):
		return self._send_data('get_mime_types', data)['mime_types']
