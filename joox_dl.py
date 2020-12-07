import argparse
import sys
import os
import requests
from tqdm import tqdm
import json
import music_tag
import configparser

## pyinstaller --onefile --icon=logo.ico .\joox_dl.py ##
m4a = None
highQuality = None
counter = 0

configParser = configparser.RawConfigParser()
configFilePath = r'joox_dl.cfg'
configParser.read(configFilePath)

# download funtion 
def downloadUrl(url, output_path):
    # url = "http://www.ovh.net/files/10Mb.dat" #big file test
    # Streaming, so we can iterate over the response.
    r = requests.get(url, stream=True)
    # Total size in bytes.
    total_size = int(r.headers.get('content-length', 0))
    block_size = 1024 #1 Kibibyte
    t=tqdm(total=total_size, unit='iB', unit_scale=True, desc=f'Downloading - {output_path}')
    with open(output_path, 'wb') as f:
        for data in r.iter_content(block_size):
            t.update(len(data))
            f.write(data)
    t.close()
    if total_size != 0 and t.n != total_size:
        return False
    return True

# clean value from restricted symbol create folder name etc.
def cleanText(textRaw):
    textClean = textRaw.replace('?', '');
    textClean = textClean.replace('\'', '');
    textClean = textClean.replace('\"', '');
    textClean = textClean.replace(':', '');
    textClean = textClean.replace('®', '');
    textClean = textClean.replace('ñ', 'n');
    textClean = textClean.replace('/', '-');

    return textClean

def getTrack(songId, albumName = None):
    
    with requests.Session() as s:
        login = s.get("https://api.joox.com/web-fcgi-bin/web_wmauth?country=id&lang=id&wxopenid=" + configParser.get('login', 'wxopenid') + "&password=" + configParser.get('login', 'password') + "&wmauth_type=0&authtype=2&time=1598864049294&_=1598864049295&callback=axiosJsonpCallback4")
        urlTrack = "http://api.joox.com/web-fcgi-bin/web_get_songinfo?songid=" + songId

        r = s.get(urlTrack)

        dataTrackRaw = r.text
        dataTrackRaw = dataTrackRaw[dataTrackRaw.find("(")+1:-1]

        dataTrack = json.loads(dataTrackRaw)

        if(dataTrack['msg'] == "invaid cookie") :
            print(dataTrack['msg'])
            exit()

        dataTrack['msong'] = cleanText(dataTrack['msong'])

        urlAdditionalDataTrack = s.get("https://api-jooxtt.sanook.com/page/single?regionURI=id-id&country=id&lang=id&id=YEPkJhasS%2B3KfmC1kyEEag%3D%3D&device=desktop")
        additionalDataTrack = json.loads(urlAdditionalDataTrack.text)
        additionalDataTrack = additionalDataTrack['single']

        if m4a:
            link_track = dataTrack['m4aUrl']
        elif (highQuality and dataTrack['has_hq']):
            link_track = dataTrack['r320Url']
        else:
            link_track = dataTrack['mp3Url']
        
        fileType = link_track.split('?')
        fileType = fileType[0].split('.')
        fileType = fileType[-1]


        global counter
        counter += 1
        fileName = dataTrack['msong'] + '.' + fileType

        if albumName:
            fileName = str(counter).zfill(2) + '. ' + fileName
            folderPath = 'music/'+ albumName
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)
            fullPath = 'music/'+ albumName + '/' + fileName
        else:
            folderPath = 'music'
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)
            fullPath = 'music/'+ fileName

        if(downloadUrl(link_track, fullPath)):
            audiofile = music_tag.load_file(fullPath)
            audiofile['artist'] = dataTrack['msinger']
            audiofile['album'] = dataTrack['malbum']
            audiofile['albumartist'] = dataTrack['msinger']
            audiofile['tracktitle'] = dataTrack['msong']
            audiofile['genre'] = additionalDataTrack['genre']
            audiofile['year'] = str(additionalDataTrack['release_time'])
            audiofile['comment'] = 'Generated By j4r1s'
            if(additionalDataTrack['lrc_exist'] == 1):
                audiofile['lyrics'] = additionalDataTrack['lrc_content']

            if (dataTrack['imgSrc'] != ""):
                responseImg = s.get(dataTrack['imgSrc'])
                mime_type = contentType = responseImg.headers['content-type']
                img = responseImg.content
                audiofile['artwork'] = img

            audiofile.save()

        return dataTrack

def main():
    parser = argparse.ArgumentParser();
    parser.add_argument('-p', '--playlist', help='Playlist ID ex. (db1J7YbWZ1LectFJqPzd5g==)')
    parser.add_argument('-a', '--album', help='Album ID ex. (fnIkeDK++hFXaAzg7s9Etg==)')
    parser.add_argument('-s', '--song', help='Song ID ex. (TtEH_iaoAGl1dh5KsV44pg==)')
    parser.add_argument('-ar', '--artist', help='Artist ID ex. (oPx7SaQaTLhpqJP1zpTSpQ==)')
    parser.add_argument('-hq', '--highquality', help='High quality', action='store_true')
    parser.add_argument('-m4a', '--m4a', help='M4A Type', action='store_true')
    args = parser.parse_args()
    playlistEncode = vars(args)['playlist']
    albumEncode = vars(args)['album']
    songEncode = vars(args)['song']
    artistEncode = vars(args)['artist']
    global highQuality
    highQuality = vars(args)['highquality']
    global m4a
    m4a = vars(args)['m4a']


    if playlistEncode:
        uri = "https://api-jooxtt.sanook.com/openjoox/v1/playlist/" + playlistEncode + "/tracks?country=id&lang=id&index=0&num=50"
    elif albumEncode :
        uri = "https://api-jooxtt.sanook.com/openjoox/v1/album/" + albumEncode + "/tracks?country=id&lang=id&index=0&num=50"        
    elif artistEncode :
        uri = "https://api-jooxtt.sanook.com/page/artistDetail?id=" + artistEncode + "&lang=id&country=id"        
    elif songEncode :
        uri = "single"
    else:
        uri = None

    if uri == None:
        parser.print_help()
        parser.exit()

    else:
        if songEncode: 
            # downloading track
            song = getTrack(songEncode)
            print(song['msong'] + ' - Selesai!') 
        elif artistEncode:
            r = requests.get(uri)
            data = r.json()
            albumName = cleanText(data['artistInfo']['name'])

            for item in data['artistTracks']['tracks']['items']:
                # downloading track
                getTrack(item['id'], albumName)

                # break
            print(albumName + ' : ' + str(data['artistTracks']['tracks']['list_count']) + ' lagu.' + ' - Selesai!')
        else :
            # fecthing track
            r = requests.get(uri)
            data = r.json()

            for item in data['tracks']['items']:
                # downloading track
                albumName = cleanText(data['name'])
                getTrack(item['id'], albumName)

                # break
            print(data['name'] + ' : ' + str(data['tracks']['list_count']) + ' lagu.' + ' - Selesai!')
        
if __name__ == '__main__': 
    try:
        main() 
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except requests.ConnectionError as e:
        print("OOPS!! Connection Error. Make sure you are connected to Internet. Technical Details given below.\n")
        print(str(e))
    except requests.Timeout as e:
        print("OOPS!! Timeout Error")
        print(str(e))
    except requests.RequestException as e:
        print("OOPS!! General Error")
        print(str(e))