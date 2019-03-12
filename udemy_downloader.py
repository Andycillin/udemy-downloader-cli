import requests, os, getpass, pickle, re, sys, getopt

selected_course_id = None
lectures_of_selected_course = []
enrolled_courses = []
selected_course = None
session = None
download_dir = os.path.join(os.getcwd(), 'udemy-downloads')
internal_state_file = os.path.join(os.getcwd(), 'istates.pkl')
downloaded_courses = []
downloaded_lectures = []
access_token = None
host = None
_host = None
showlog = False

if os.path.exists(internal_state_file):
    istate_file = open(internal_state_file, 'rb')
    downloaded_courses, downloaded_lectures, host, access_token = pickle.load(istate_file)
    istate_file.close()

try:
    opts, args = getopt.getopt(sys.argv[1:], "s:ln", ["server=", "showlog", "new_user"])
except getopt.GetoptError:
    print('udemy_downloader.py -s <server> -l <True|False>')
    sys.exit(2)

for opt, arg in opts:
    if opt in ("-s", "--server"):
        _host = arg
    elif opt in ("-l", "--showlog"):
        showlog = True
    elif opt in ("-n", "--new_user"):
        access_token = None


def set_access_token(token):
    headers['Authorization'] = 'Bearer ' + token
    headers['X-Udemy-Authorization'] = 'Bearer ' + token


def login(session):
    global access_token
    if access_token != None:
        print("Access token found !")
        set_access_token(access_token)
    else:
        csrftoken = get_csrf_token(session)
        print('''
------------------
| Authentication |
------------------
        ''')
        email = input("Email: ")
        password = getpass.getpass()
        print_update("Logging in...")
        r2 = session.post(login_url,
                          data={'email': email, 'password': password,
                                'csrfmiddlewaretoken': csrftoken}, headers=headers)
        if 'access_token' not in r2.cookies:
            found_token = False
            for h in r2.history:
                if 'access_token' in h.cookies:
                    found_token = True
                    access_token = h.cookies['access_token']
                    set_access_token(access_token)
                    break
            if not found_token:
                print("Access denied!")
                exit(0)

        else:
            access_token = r2.cookies['access_token']
            set_access_token(access_token)
        print('Access granted!')
        persist_internal_state()


def get_csrf_token(session):
    global base_api_url
    print_update("Connecting...")
    try:
        x = session.get(base_api_url + '/join/login-popup/')
        csrftoken = session.cookies['csrftoken']
        headers['csrftoken'] = csrftoken
        print_update("Connection established!")
        return csrftoken
    except:
        print("Failed to connect to " + base_api_url)
        exit(0)


def get_enrolled_courses(session, arglist=[], silent=False):
    global enrolled_courses, access_token
    if silent:
        print_update('Preparing your workbench...')
    r5 = session.get(enrolled_courses_url)
    if r5.status_code != 200:
        access_token = None
        print_last_update("Access token expired or invalid. You must login again")
        login(session)
    else:
        courses = r5.json()['results']
        enrolled_courses = courses
        if not silent:
            print('''
            --------------------
            | Enrolled courses |
            --------------------
            ''')
            if (len(courses) == 0):
                print("You've not enrolled in any course")
            else:
                print("Enrolled courses:")
                print("-" * 20)
                print("%-10s%s" % ('ID', 'Title'))
                for c in courses:
                    cname = c['title']
                    if c['id'] in downloaded_courses:
                        cname = "(Downloaded) " + cname
                    print('%-10s%s' % (c['id'], cname))
                print("-" * 20)
    if silent:
        print_last_update('Ready!')
        print('\n' + '-' * 20)


# Included chapters
def get_lectures_of_course(session, courseid):
    r3 = session.get(course_lectures_url % (courseid))
    if 'results' not in r3.json():
        print("Error: Course not found")
        exit(0)
    # lectures = [item for item in r3.json()['results'] if item['_class'] == 'lecture']
    lectures = [item for item in r3.json()['results'] if item['_class'] in ['lecture', 'chapter']]
    return lectures


def split_lectures_to_chapters(lectures):
    chapters = []
    chapter = []
    for idx, item in enumerate(lectures):
        if item['_class'] == 'chapter' and idx > 0:
            chapters.append(chapter)
            chapter = []
        chapter.append(item)
    return chapters


'''
First item is chapter item
All others are lectures
'''


def download_chapter(session, courseid, section):
    print('Downloading Chapter ' + str(section[0]['object_index']) + ' - ' + section[0]['title'])
    chap_dir = get_chapter_dir(section[0])
    lectures = section[1:]
    for idx, l in enumerate(lectures):
        get_assets_of_lecture(session, courseid, l, chap_dir, idx, len(lectures))


def get_chapter_dir(chapter):
    if not os.path.isdir(download_dir):
        os.makedirs(download_dir)

    chapter_number = chapter['object_index']
    chapter_dir = os.path.join(get_course_dir(),
                               clean_string(
                                   'Chapter ' + str(chapter_number) + ' - ' + replace_space(chapter['title'])))
    if not os.path.isdir(chapter_dir):
        os.makedirs(chapter_dir)
    return chapter_dir


def replace_space(s):
    return '-'.join(s.split(' '))


def get_course_dir():
    if not os.path.isdir(download_dir):
        os.makedirs(download_dir)
    dir = os.path.join(download_dir,
                       clean_string(
                           str(selected_course['id']) + '_' + replace_space(selected_course['title'])))
    if not os.path.isdir(dir):
        os.makedirs(dir)
    return dir


def get_assets_of_lecture(session, courseid, lecture, to_dir, idx=1, total=1):
    if (str(courseid) + '_' + str(lecture['id']) in downloaded_lectures):
        print_update("Already downloaded this lecture (%s). Skipping..." % (str(lecture['id'])))
        return

    if len(lecture['supplementary_assets']) > 0:
        print_update('%s has %d supplementary asset' % (lecture['title'], len(lecture['supplementary_assets'])))
        for a in lecture['supplementary_assets']:
            download_asset(session, courseid, lecture, a, to_dir)
    r4 = session.get(assets_of_lecture_url % (courseid, lecture['id']))
    try:
        asset = r4.json()['asset']
    except:
        print(r4)
        print("An error occured. I'm out")
        sys.exit(1)

    if (asset['asset_type'] == 'Video'):
        url = asset['stream_urls']['Video'][0]['file']
        ext = url.split('/')[-1].split('?')[0].split('.')[-1]
        vid_name = clean_string(str(lecture['object_index']) + '_Lecture-' + '-'.join(lecture['title'].split(' ')))
        vid_filename = vid_name + '.' + ext
        filename = os.path.join(to_dir, vid_filename)
        sys.stdout.write("\033[K")
        print_update("(%d/%d) Downloading video: %s" % (idx + 1, total, vid_filename))
        if showlog:
            print("URL: ", url)
        # vid = session.get(url)
        vid = requests.get(url)
        if vid.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(vid.content)
        else:
            print("Error Code: ", vid.status_code)
            print(vid.text)
    downloaded_lectures.append(str(courseid) + '_' + str(lecture['id']))


def download_asset(session, courseid, lecture, asset, to_dir):
    lectureid = lecture['id']
    is_video = False
    if asset['asset_type'] == 'ExternalLink':
        print_update("Saving URL: %s ..." % (asset['filename']))
        filename = 'URL_' + asset['filename']
        ext = 'txt'
        content = asset['external_url']
    else:
        print_update("Downloading file: %s ... " % (asset['filename']))
        filename, ext = tuple(asset['filename'].rsplit('.', 1))
        is_video = True

    filepath = os.path.join(to_dir, clean_string(str(lecture['object_index']) + '_Asset-' + filename) + '.' + ext)

    if is_video:
        r = session.get(download_asset_url % (courseid, lectureid, asset['id']))
        try:
            urls = r.json()['download_urls']
            # content = session.get(urls['File'][0]['file'])
            if showlog:
                print("URL: ", urls['File'][0]['file'])
            content = requests.get(urls['File'][0]['file'])
            if content.status_code == 200:
                open(filepath, 'wb').write(content.content)
            else:
                print("Error Code: ", content.status_code)
                print(content.text)
        except:
            print(r)
    else:
        open(filepath, 'w').write(content)

    # print("Saved: ", asset['filename'])


def download_all_from_course(session):
    print("Course: %s | ID: %s" % (selected_course['title'], selected_course['id']))
    if selected_course_id in downloaded_courses:
        print("Already downloaded this course. Skipping...")
        return
    lectures = get_lectures_of_course(session, selected_course_id)
    chapters = split_lectures_to_chapters(lectures)
    print("Downloading all %d chapters and supplementaries..." % (len(chapters)))

    for c in chapters:
        download_chapter(session, selected_course_id, c)
    downloaded_courses.append(selected_course_id)
    persist_internal_state()
    print("Successfully downloaded all lectures!")


def download_single_lecture_from_course(session, lecture):
    print("Downloading lecture: %s" % (lecture['title']))
    get_assets_of_lecture(session, selected_course_id, lecture, get_course_dir(), 1, 1)


def cmd_download(session, args_list, greet=True):
    assert len(args_list) == 1
    download_all = args_list[0].lower() == 'all'
    if download_all:
        if greet:
            print('''
                    -------------------------
                    | DOWNLOAD ALL LECTURES |
                    -------------------------
                    ''')
        download_all_from_course(session)
    else:
        found = False
        for l in lectures_of_selected_course:
            if int(l['id']) == int(args_list[0]):
                found = True
                if greet:
                    print('''
                                    ----------------------
                                    |  DOWNLOAD LECTURE  |
                                    ----------------------
                                    ''')
                download_single_lecture_from_course(session, l)

                print("Successfully downloaded lecture: %s!" % (l['title']))
                break
        if not found:
            print("Lecture not found. Are you sure that LectureID is correct?")


def cmd_select_course(session, args_list, silent = False):
    global lectures_of_selected_course, selected_course_id, selected_course
    course_id = int(args_list[0])
    found = False
    for c in enrolled_courses:
        if c['id'] == course_id:
            found = True
            selected_course = c
            break
    if found:
        lectures_of_selected_course = get_lectures_of_course(session, course_id)
        selected_course_id = course_id
        if not silent:
            cmd_list_all_lectures(session, args_list)
    else:
        print('Course with ID %d not found' % (int(c['id'])))


def cmd_list_all_lectures(session, args_list):
    print('-' * (len(selected_course['title']) + 4))
    print('  ' + selected_course['title'])
    print('-' * (len(selected_course['title']) + 4))
    print("%-10s%s" % ('ID', 'Lecture title'))
    print("-" * 20)
    for l in lectures_of_selected_course:
        print("%-10s%s" % (l['id'], l['title']))
    print("-" * 20)
    # print("Type 'download all' or 'download <LectureID> to save videos and assets to your computer")


def cmd_downloadall(session, args_list):
    global enrolled_courses
    for c in enrolled_courses:
        cmd_select_course(session, [c['id']], silent=True)
        cmd_download(session, ['all'], False)


cmd_list = {
    'download': {
        'require_course': True,
        'func': cmd_download
    },
    'lectures': {
        'require_course': True,
        'func': cmd_list_all_lectures
    },
    'select': {
        'require_course': False,
        'func': cmd_select_course
    },
    'downloadall': {
        'require_course': False,
        'func': cmd_downloadall
    },
    'list': {
        'require_course': False,
        'func': get_enrolled_courses
    }
}


def loop_user_interaction(session):
    global selected_course_id
    print("Type 'select <CourseID>' to select a course")
    while True:
        print("Enter command:")
        inp = input(">")
        parts = inp.split(" ")
        cmd = parts[0]
        args = parts[1:]
        if (cmd.lower() == 'exit'):
            break
        if (cmd in cmd_list):
            if (cmd_list[cmd]['require_course'] and selected_course_id == None):
                print("No course is selected yet. use command: select <CourseID> first")
            else:
                cmd_list[cmd]['func'](session, args)
        else:
            print("Unknown command:", cmd)


def build_env(host):
    global udemy_host, base_api_url, login_url, download_asset_url, \
        enrolled_courses_url, course_lectures_url, assets_of_lecture_url, \
        session, headers
    if (len(host.strip(' ')) == 0):
        udemy_host = 'www.udemy.com'
    else:
        udemy_host = host.strip(' ')
    base_api_url = "https://" + udemy_host
    login_url = base_api_url + "/join/login-popup/"
    download_asset_url = base_api_url + "/api-2.0/users/me/subscribed-courses/%d/lectures/%d/supplementary-assets/%d?fields[asset]=download_urls"
    enrolled_courses_url = base_api_url + "/api-2.0/users/me/subscribed-courses?fields%5Bcourse%5D=@min,visible_instructors,image_240x135,image_480x270,favorite_time,archive_time,completion_ratio,last_accessed_time,enrollment_time,is_practice_test_course,features,num_collections,published_title&fields%5Buser%5D=@min,job_title&ordering=-access_time,-enrolled&page=1&page_size=1400"
    course_lectures_url = base_api_url + "/api-2.0/courses/%d/cached-subscriber-curriculum-items/?page_size=1400&fields[lecture]=@min,object_index,asset,supplementary_assets,sort_order,is_published,is_free&fields[quiz]=@min,object_index,title,sort_order,is_published&fields[practice]=@min,object_index,title,sort_order,is_published&fields[chapter]=@min,description,object_index,title,sort_order,is_published&fields[asset]=@min,title,filename,asset_type,external_url,length,status"
    assets_of_lecture_url = base_api_url + "/api-2.0/users/me/subscribed-courses/%d/lectures/%d?fields[asset]=@min,download_urls,external_url,slide_urls,status,captions,thumbnail_url,time_estimation,stream_urls&fields[caption]=@default,is_translation&fields[course]=id,url,locale&fields[lecture&=@default,course,can_give_cc_feedback,can_see_cc_feedback_popup,download_url"
    session = requests.Session()
    headers = {'authority': udemy_host,
               'cache-control': 'max-age=0',
               'upgrade-insecure-requests': '1',
               'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
               'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
               'accept-encoding': 'gzip, deflate, br',
               'accept-language': 'en-US,en;q=0.9,de;q=0.8,vi;q=0.7',
               'referer': base_api_url + '/'
               }
    session.headers = headers


def persist_internal_state():
    istate_file = open(internal_state_file, 'wb')
    pickle.dump((downloaded_courses, downloaded_lectures, host, access_token), istate_file)
    istate_file.close()


def greeting():
    print('''
===========================
||                       ||
|| UDEMY DOWNLOADER V1.3 ||
||       Andy Tran       ||
===========================
    ''')


def clean_string(path):
    return re.sub('[^\d\w\-_]+', '', path)


def clear_last_line():
    sys.stdout.write("\033[K")


def print_update(*pargs):
    clear_last_line()
    print(*pargs, end='\r', flush=True)


def print_last_update(*pargs):
    clear_last_line()
    print(*pargs)


greeting()
if _host == None:
    _host = input("Udemy Server (default www.udemy.com):")
if _host != host:
    access_token = None
    host = _host
build_env(host)
login(session)
get_enrolled_courses(session, silent=True)
loop_user_interaction(session)
