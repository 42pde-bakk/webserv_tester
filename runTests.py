# Tester dedicated to the 42 project webserv.
# 01/11/2020
# Feel free to use it, just be sure that configuration file is properly set

# For leaks (after having set an exit() call on a relevant place) :
# valgrind --track-origins=yes --leak-check=full --log-file="output" --show-leak-kinds=all ./webserv conf/default.conf
# leaks webserv --fullStacks --fullContent

# wget http://download.joedog.org/siege/siege-latest.tar.gz - tar -xcvf

# Score :
# Official Tester : < 15 minutes (full logs)

# Usage : runTests.py [METHOD] [TEST NUM] [VERBOSE]
# python3 runTests.py
# python3 runTests.py GET
# python3 runTests.py PUT
# python3 runTests.py GET 2
# python3 runTests.py GET 7
# python3 runTests.py GET 7 -v

# ---------------------------------------------------------------------------
# ---------------------------- 1. CHECKS ------------------------------------
# ---------------------------------------------------------------------------

import os
import sys
import json
import requests
import base64
import shutil

from requests.auth import HTTPBasicAuth
from sys import platform

global verbose
verbose = 0

if len(sys.argv) == 4 and sys.argv[3] == '-v':
	verbose = 1
if os.system('lsof -c webserv > /dev/null') != 0:
	print("Webserv is not running")
	exit()
if os.system('type php-cgi > /dev/null') != 0:
	print(
		"The executable php-cgi is required to run theses tests.\nBe sure that the php-cgi path inside the configuration file is correct")
	exit()


# ---------------------------------------------------------------------------
# ----------------------------- 2. CORE -------------------------------------
# ---------------------------------------------------------------------------

class AssertTypes:
	BODY_CONTAIN_ASSERT = 1
	FILE_CONTAIN_ASSERT = 2
	RES_HD_CONTAIN_ASSERT = 3
	RESOURCE_SHOULD_EXIST_ASSERT = 4
	RESOURCE_SHOULD_NOT_EXIST_ASSERT = 5


class Bcolors:
	HEADER = '\033[95m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'


def b64e(s):
	return base64.b64encode(s.encode()).decode()


def b64d(s):
	return base64.b64decode(s).decode()


def printHdReqRes(r):
	print()
	indent = "          Request >  "
	for idA, reqKey in enumerate(r.request.headers):
		print(indent + reqKey + ": " + r.request.headers[reqKey])
	print()
	indent = "          Response > "
	for idB, resKey in enumerate(r.headers):
		print(indent + resKey + ": " + r.headers[resKey])
	print()


# ------------------------ ANNEXES FUNCTIONS  -------------------------------

def createFile(path, content):
	file = open(path, 'w')
	file.write(content)
	file.close()


def createDirectory(path, dirName, withFiles, withSubDir):
	if os.path.exists(path + dirName + "/"):
		shutil.rmtree("www/deleteTests/")
	os.mkdir(path + dirName)
	if withFiles:
		createFile(path + dirName + "/file1", "test delete")
		createFile(path + dirName + "/file2", "test delete")
	if withSubDir:
		os.mkdir(path + dirName + "/subDir1/")
		createFile(path + dirName + "/subDir1/file1", "test delete")
		createFile(path + dirName + "/subDir1/file2", "test delete")
		os.mkdir(path + dirName + "/subDir2/")
		createFile(path + dirName + "/subDir2/file1", "test delete")
		createFile(path + dirName + "/subDir2/file2", "test delete")


# ------------------------ ASSERT FUNCTIONS  -------------------------------

def bodyContain(r, string):
	return string in r.text


def fileContain(strLookingFor, path):
	file = open(path, 'r').read()
	return strLookingFor in file


def resHeadersKeyVal(r, hdKeyTab=None, hdValTab=None):
	if hdValTab is None:
		hdValTab = []
	if hdKeyTab is None:
		hdKeyTab = []
	validated = 0
	for idA, resKey in enumerate(r.headers):
		for idB, wantKey in enumerate(hdKeyTab):
			if wantKey == resKey and hdValTab[idB] in r.headers[resKey]:
				validated += 1
	return validated == len(hdKeyTab)


def resourceExist(resource):
	return os.path.exists(resource)


def moreAsserts(r, assertLevel, *args):
	indexArgsUsed = 0
	ret = False
	if AssertTypes.BODY_CONTAIN_ASSERT in assertLevel and bodyContain(r, args[0][indexArgsUsed]):
		ret = True
		indexArgsUsed += 1
	if AssertTypes.FILE_CONTAIN_ASSERT in assertLevel and fileContain(args[0][indexArgsUsed], args[0][indexArgsUsed + 1]):
		ret = True
		indexArgsUsed += 2
	# print(f' if {AssertTypes.RES_HD_CONTAIN_ASSERT in assertLevel} and {resHeadersKeyVal(r, args[0][indexArgsUsed], args[0][indexArgsUsed + 1])}')
	if AssertTypes.RES_HD_CONTAIN_ASSERT in assertLevel and resHeadersKeyVal(r, args[0][indexArgsUsed], args[0][indexArgsUsed + 1]):
		ret = True
		indexArgsUsed += 2
	if AssertTypes.RESOURCE_SHOULD_EXIST_ASSERT in assertLevel and resourceExist(args[0][indexArgsUsed]):
		ret = True
		indexArgsUsed += 1
	if AssertTypes.RESOURCE_SHOULD_NOT_EXIST_ASSERT in assertLevel and not resourceExist(args[0][indexArgsUsed]):
		ret = True
		indexArgsUsed += 1

	return ret


def assertResponse(r, code, index, assertLevel=None, *args):
	if assertLevel is None:
		assertLevel = []
	var = False
	if len(assertLevel):
		ret = moreAsserts(r, assertLevel, args)
	else:
		ret = True
	if ret and r.status_code == code:
		info = Bcolors.OKGREEN + "OK" + Bcolors.ENDC + " - " + str(r.status_code) + " " + r.raw.reason
	else:
		info = Bcolors.FAIL + "KO" + Bcolors.ENDC + " - " + str(
			r.status_code) + " " + r.raw.reason + " - Should have been received : " + str(code)
	url = "           • #" + str(index).ljust(2, ' ') + " : " + str(r.request.method) + " "
	if len(r.request.url) > 60:
		url += r.request.url[16:60] + " [..." + str(len(r.request.url)) + "]"
	else:
		url += str(r.request.url)[16:]
	url = str(url).ljust(80, ' ')
	print(url + "   =   " + info)
	if verbose == 1:
		printHdReqRes(r)


def run(Sys):
	print("\n       Platform = " + platform)
	if len(Sys.argv) == 1:
		GET_TESTS()
		POST_TESTS()
		PUT_TESTS()
		DELETE_TESTS()
		HEAD_TESTS()
	elif len(Sys.argv) == 2:
		if Sys.argv[1] == "GET":
			GET_TESTS()
		elif Sys.argv[1] == "HEAD":
			HEAD_TESTS()
		elif Sys.argv[1] == "POST":
			POST_TESTS()
		elif Sys.argv[1] == "PUT":
			PUT_TESTS()
		elif Sys.argv[1] == "DELETE":
			DELETE_TESTS()
	elif len(Sys.argv) >= 3:
		if Sys.argv[1] == "GET":
			GET_TESTS(Sys.argv[2])
		elif Sys.argv[1] == "HEAD":
			HEAD_TESTS(Sys.argv[2])
		elif Sys.argv[1] == "POST":
			POST_TESTS(Sys.argv[2])
		elif Sys.argv[1] == "PUT":
			PUT_TESTS(Sys.argv[2])
		elif Sys.argv[1] == "DELETE":
			DELETE_TESTS(Sys.argv[2])
	print()


# -----------------------------------------------------------------------------
# ------------------------------------ GET ------------------------------------
# -----------------------------------------------------------------------------

def GET_TESTS(testNum=0):
	index = 0
	print("\n     ~ GET REQUESTS ------------------------> \n")

	#  r = requests.get("http://localhost:7070") is turned in HTTP
	# request by Python, into this :

	# GET / HTTP/1.1
	# Host: localhost:7070
	# User-Agent: python-requests/2.24.0
	# Accept-Encoding: gzip, deflate
	# Accept: */*
	# Connection: keep-alive

	# ------- GET : 200 (without CGI)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070")
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/index.html")
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/?a=1&b=2")
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/?a=z??a=1&b=2?")
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/php")
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/php/index.html")
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/ftcgi/index.html")
		assertResponse(r, 200, index)

	# ------- GET : 200 (with CGI)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/index.bla")
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/ftcgi/index.bla")
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/php/uriQueries.php?user=bob")
		assertResponse(r, 200, index, [AssertTypes.BODY_CONTAIN_ASSERT], "bob")
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/php/info.php")
		assertResponse(r, 200, index)

	# ------- GET : Authentification
	# Auth : root:pass = cm9vdDpwYXNz (base64)
	index += 1
	if testNum == 0 or index == int(testNum):
		auth = 'Basic ' + b64e('peer:wrongpassword')
		hd = {
			"Authorization": auth,
			"Connection": "close",
		}
		r = requests.get("http://localhost:7070/auth", headers=hd)
		assertResponse(r, 401, index, [AssertTypes.RES_HD_CONTAIN_ASSERT], ["WWW-Authenticate"], ["Basic"])
	index += 1
	if testNum == 0 or index == int(testNum):
		auth = 'Basic ' + b64e('peer:super')
		hd = {
			"Authorization": auth,
			"Connection": "close",
		}
		r = requests.get("http://localhost:7070/auth/index.html", headers=hd)
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		auth = 'Basic ' + b64e('peer:wrong')
		hd = {
			"Authorization": auth,
			"Connection": "close",
		}
		r = requests.get("http://localhost:7070/auth", headers=hd)
		assertResponse(r, 401, index, [AssertTypes.RES_HD_CONTAIN_ASSERT], ["WWW-Authenticate"], ["Basic"])
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/auth", auth=HTTPBasicAuth('peer', 'super'), headers={})
		assertResponse(r, 200, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		auth = 'Basic ' + b64e('peer:wrong')
		hd = {
			"Authorization": auth,
			"Connection": "close",
		}
		r = requests.get("http://localhost:7070/auth", headers=hd)
		assertResponse(r, 401, index, [AssertTypes.RES_HD_CONTAIN_ASSERT], ["WWW-Authenticate"], ["Basic"])

	# ------- GET : Negotiation
	index += 1
	if testNum == 0 or index == int(testNum):
		hd = {"Accept-Language": "fr"}
		r = requests.get("http://localhost:7070/nego", headers=hd)
		assertResponse(r, 200, index, [AssertTypes.BODY_CONTAIN_ASSERT], "FRANCE")
	index += 1
	if testNum == 0 or index == int(testNum):
		hd = {"Accept-Language": "en"}
		r = requests.get("http://localhost:7070/nego", headers=hd)
		assertResponse(r, 200, index, [AssertTypes.BODY_CONTAIN_ASSERT], "ENGLAND")
	index += 1
	if testNum == 0 or index == int(testNum):
		hd = {"Accept-Language": "de"}
		r = requests.get("http://localhost:7070/nego", headers=hd)
		assertResponse(r, 200, index, [AssertTypes.BODY_CONTAIN_ASSERT], "NO_LANGUAGE_NEGOTIATED")

	# ------- GET : 40X

	index += 1
	if testNum == 0 or index == int(testNum):
		hd = {"Host": ''}
		r = requests.get("http://localhost:7070/", headers=hd)
		assertResponse(r, 400, index)

	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/inexisting")
		assertResponse(r, 404, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/nego/xxxxxx")
		assertResponse(r, 404, index)
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/ftcgi/.bla")
		assertResponse(r, 404, index)

	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/...")
		assertResponse(r, 400, index)

	# ------- GET : 41X

	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get(
			"http://localhost:7070/?queries=zyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcba")
		assertResponse(r, 414, index)

	# ------- GET : AutoIndex

	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/auto")
		assertResponse(r, 404, index, [AssertTypes.BODY_CONTAIN_ASSERT], "error")
		# Changed status code to 404 because nginx nginx only autoindex if the uri ends with a '/'
		# Source: http://nginx.org/en/docs/http/ngx_http_autoindex_module.html

	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/auto/")
		assertResponse(r, 200, index, [AssertTypes.BODY_CONTAIN_ASSERT], "index.html")

	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/auto/index.html")
		assertResponse(r, 200, index, [AssertTypes.BODY_CONTAIN_ASSERT], "Welcome to Webserv!")

	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/auto/test42/")
		assertResponse(r, 200, index, [AssertTypes.BODY_CONTAIN_ASSERT], "Error")

	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.get("http://localhost:7070/auto/xxx")
		assertResponse(r, 404, index)  # ---> Potentiellement à modifier


# -----------------------------------------------------------------------------
# ----------------------------------- POST ------------------------------------
# ------------- WARNING : POST Tests are dependant each other -----------------
# -----------------------------------------------------------------------------

def POST_TESTS(testNum=0):
	index = 0
	print("\n     ~ POST REQUESTS -----------------------> \n")

	# ------- POST - 200/201 - NO CGI
	newFilePath = '../webserv/htmlfiles/newFile'  # change this!
	index += 1
	platform = "darwin"
	if testNum == 0 or index == int(testNum):  # 1
		if os.path.exists(newFilePath):
			os.remove(newFilePath)
		payload = "Hello ! I am a new file\r\n\r\n"
		r = requests.post('http://localhost:7070/newFile', data=payload, headers={})
		assertResponse(r, 201, index, [AssertTypes.FILE_CONTAIN_ASSERT], "Hello ! I am a new file", newFilePath)
	index += 1
	if testNum == 0 or index == int(testNum):  # 2
		payload = ". I have been updated !\r\n\r\n"
		r = requests.post('http://localhost:7070/newFile', data=payload, headers={})
		assertResponse(r, 200, index, [AssertTypes.FILE_CONTAIN_ASSERT], "Hello ! I am a new file. I have been updated !", newFilePath)
	index += 1
	if platform == "darwin" and testNum == 0 or index == int(testNum):  # 3
		if os.path.exists(newFilePath):
			os.remove(newFilePath)
		payload = {'hello': 'world'}
		pl = json.dumps(payload) + '\r\n\r\n'
		hd = {"Content-Type": "application/json"}
		r = requests.post('http://localhost:7070/newFile', data=pl, headers=hd)
		assertResponse(r, 201, index, [AssertTypes.FILE_CONTAIN_ASSERT], "{\"hello\": \"world\"}", newFilePath)

	# ------- POST CHUNKED - 200/201 - NO CGI

	# Note that if a message is received with both a Transfer-Encoding header field and a Content-Length header field, the latter MUST be ignored.
	index += 1
	if platform == "darwin" and (testNum == 0 or index == int(testNum)):  # 4
		if os.path.exists(newFilePath):
			os.remove(newFilePath)
		payload = "14\r\nabcdefghijklmnopqrst\r\nA\r\n0123456789\r\n0\r\n\r\n"
		hd = {'Transfer-Encoding': 'chunked'}
		print(index)
		r = requests.post("http://localhost:7070/newFile", data=payload, headers=hd)
		assertResponse(r, 201, index, [AssertTypes.FILE_CONTAIN_ASSERT], "abcdefghijklmnopqrst0123456789", newFilePath)
	index += 1
	if platform == "darwin" and (testNum == 0 or index == int(testNum)):  # 5
		payload = "14\r\nabcdefghijklmnopqrst\r\nA\r\n0123456789\r\n0\r\n\r\n"
		hd = {'Transfer-Encoding': 'chunked'}
		r = requests.post("http://localhost:7070/newFile", data=payload, headers=hd)
		assertResponse(r, 200, index, [AssertTypes.FILE_CONTAIN_ASSERT], "abcdefghijklmnopqrst0123456789abcdefghijklmnopqrst0123456789", newFilePath)

	# ------- POST - 200/2001 - 42 CGI
	index += 1
	if testNum == 0 or index == int(testNum):  # 6
		payload = "I am a payload\r\n\r\n"
		r = requests.post('http://localhost:7070/ftcgi/index.bla', data=payload, headers={})
		assertResponse(r, 200, index, [AssertTypes.BODY_CONTAIN_ASSERT], "I AM A PAYLOAD")

	# FREEZE ERROR

	# ------- POST IMGAGE CHUNKED - 201
	# index += 1
	# if (testNum == 0 or index == int(testNum)):
	#     if os.path.exists("www/42.png"): os.remov5e("www/42.png")
	#     img = {'file': open('test/payloads/42.png', 'rb')}
	#     hd = {"Content-Type": "image/png", "Transfer-Encoding": "chunked"}
	#     r = requests.post('http://localhost:7070/youpi/pouet/42.png', files=img,  headers=hd)
	#     assertResponse(r, 201, index)

	# ------- POST - REQUEST_ENTITY_TOO_LARGE_413

	index += 1
	if testNum == 0 or index == int(testNum):  # 7
		if os.path.exists("www/newFile"):
			os.remove("www/newFile")
		hd = {"Content-Type": "text/plain"}
		body = "abcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyzabcdefghijklmnopqrstuvwyz\r\n\r\n"
		r = requests.post("http://localhost:7070/newFile", body, headers=hd)
		assertResponse(r, 413, index)


# -----------------------------------------------------------------------------
# ----------------------------------- HEAD ------------------------------------
# -----------------------------------------------------------------------------

def HEAD_TESTS(testNum=0):
	index = 0
	print("\n     ~ HEAD REQUESTS -----------------------> \n")

	# ------- HEAD - 200
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.head("http://localhost:7070/")
		assertResponse(r, 200, index, [AssertTypes.RES_HD_CONTAIN_ASSERT], ["Content-Length"], ["544"])

	# ------- HEAD - 405
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.head("http://localhost:7070/ftcgi")
		assertResponse(r, 405, index, [AssertTypes.RES_HD_CONTAIN_ASSERT], ["Allow"], ["GET, POST"])


# -----------------------------------------------------------------------------
# ----------------------------------- PUT -------------------------------------
# -----------------------------------------------------------------------------

def PUT_TESTS(testNum=0):
	index = 0
	print("\n     ~ PUT REQUESTS -----------------------> \n")

	# ------- PUT - 201 CREATED
	index += 1
	newFilePath = '../webserv/htmlfiles/newFile'  # change this!
	if testNum == 0 or index == int(testNum):
		if os.path.exists(newFilePath):
			os.remove(newFilePath)
		payload = "Hello ! I am a new file\r\n\r\n"
		r = requests.put('http://localhost:7070/newFile', data=payload, headers={})
		assertResponse(r, 201, index, [AssertTypes.FILE_CONTAIN_ASSERT], "Hello ! I am a new file", newFilePath)

	# ------- PUT - 204 OK
	index += 1
	if testNum == 0 or index == int(testNum):
		payload = "Hello ! I am a modified file\r\n\r\n"
		r = requests.put('http://localhost:7070/newFile', data=payload, headers={})
		assertResponse(r, 204, index, [AssertTypes.FILE_CONTAIN_ASSERT], "Hello ! I am a modified file", newFilePath)

	# ------- PUT - 409 CONFLICT
	index += 1
	if testNum == 0 or index == int(testNum):
		payload = "Hello ! I am a new file\r\n\r\n"
		r = requests.put('http://localhost:7070/newFile/', data=payload, headers={}, timeout=1)
		assertResponse(r, 409, index, [AssertTypes.RESOURCE_SHOULD_NOT_EXIST_ASSERT], "./newFile/")

	# ------- PUT - 413
	index += 1
	if testNum == 0 or index == int(testNum):
		payload = "| test| " * 10000 + '\r\n\r\n'
		r = requests.put('http://localhost:7070/newFile', data=payload, headers={}, timeout=1)
		assertResponse(r, 413, index, [AssertTypes.RESOURCE_SHOULD_NOT_EXIST_ASSERT], "./newFile")


# -----------------------------------------------------------------------------
# ---------------------------------- DELETE -----------------------------------
# -----------------------------------------------------------------------------

def DELETE_TESTS(testNum=0):
	index = 0
	print("\n     ~ DELETE REQUESTS -----------------------> \n")

	# ------- PUT - 204 NO CONTENT
	index += 1
	if testNum == 0 or index == int(testNum):
		if not os.path.exists("www/newFile"):
			createFile("www/newFile", "Delete test")
		r = requests.delete('http://localhost:7070/newFile', data="", headers={})
		assertResponse(r, 204, index, [AssertTypes.RESOURCE_SHOULD_NOT_EXIST_ASSERT], "./newFile")

	# ------- PUT - 409 CONFLICT
	index += 1
	if testNum == 0 or index == int(testNum):
		if os.path.exists("www/newFile"):
			os.remove("www/newFile")
		r = requests.delete('http://localhost:7070/newFile', data="", headers={})
		assertResponse(r, 409, index, [AssertTypes.RESOURCE_SHOULD_NOT_EXIST_ASSERT], "./newFile")

	# ------- PUT - 409 CONFLICT
	index += 1
	if testNum == 0 or index == int(testNum):
		r = requests.delete('http://localhost:7070/deleteError/', data="", headers={})
		assertResponse(r, 409, index)

	# ------- PUT - 204 NO CONTENT
	index += 1
	if testNum == 0 or index == int(testNum):
		createDirectory("www/", "deleteTests", False, False)
		r = requests.delete('http://localhost:7070/deleteTests/', data="", headers={})
		assertResponse(r, 204, index, [AssertTypes.RESOURCE_SHOULD_NOT_EXIST_ASSERT], "./deleteTests/")

	# ------- PUT - 204 NO CONTENT
	index += 1
	if testNum == 0 or index == int(testNum):
		createDirectory("www/", "deleteTests", True, False)
		r = requests.delete('http://localhost:7070/deleteTests/', data="", headers={})
		assertResponse(r, 204, index, [AssertTypes.RESOURCE_SHOULD_NOT_EXIST_ASSERT], "./deleteTests/")

	# ------- PUT - 204 NO CONTENT
	index += 1
	if testNum == 0 or index == int(testNum):
		createDirectory("www/", "deleteTests", True, True)
		r = requests.delete('http://localhost:7070/deleteTests/', data="", headers={})
		assertResponse(r, 204, index, [AssertTypes.RESOURCE_SHOULD_NOT_EXIST_ASSERT], "./deleteTests/")


# -----------------------------------------------------------------------------
# ----------------------------------- MAIN ------------------------------------
# -----------------------------------------------------------------------------


run(sys)
