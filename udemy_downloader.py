import requests, os, getpass, pickle, re

selected_course_id = None
lectures_of_selected_course = []
enrolled_courses = []
selected_course = None
session = None
download_dir = os.path.join(os.getcwd(), 'udemy-downloads')
internal_state_file = os.path.join(os.getcwd(), 'istates.pkl')
downloaded_courses = []
downloaded_lectures = []
if os.path.exists(internal_state_file):
    istate_file = open(internal_state_file, 'rb')
    downloaded_courses, downloaded_lectures = pickle.load(istate_file)
    istate_file.close()


def login(session):
    csrftoken = get_csrf_token(session)
    print('''
    ------------------
    | Authentication |
    ------------------
    ''')
    email = input("Email: ")
    password = getpass.getpass()
    print("Logging in...")
    r2 = session.post(login_url,
                      data={'email': email, 'password': password,
                            'csrfmiddlewaretoken': csrftoken}, headers=headers)
    if 'access_token' not in r2.cookies:
        found_token = False
        for h in r2.history:
            if 'access_token' in h.cookies:
                found_token = True
                access_token = h.cookies['access_token']
                headers['Authorization'] = 'Bearer ' + access_token
                headers['X-Udemy-Authorization'] = 'Bearer ' + access_token
                break
        if not found_token:
            print("Access denied!")
            exit(0)

    else:
        access_token = r2.cookies['access_token']
        headers['Authorization'] = 'Bearer ' + access_token
        headers['X-Udemy-Authorization'] = 'Bearer ' + access_token
    print('Access granted!')


def get_csrf_token(session):
    global base_api_url
    print("Connecting...")
    try:
        x = session.get(base_api_url + '/join/login-popup/')
        csrftoken = session.cookies['csrftoken']
        headers['csrftoken'] = csrftoken
        print("Connection established!")
        return csrftoken
    except:
        print("Failed to connect to " + base_api_url)
        exit(0)


def get_enrolled_courses(session):
    global enrolled_courses
    r5 = session.get(enrolled_courses_url)
    courses = r5.json()['results']
    enrolled_courses = courses
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


def get_lectures_of_course(session, courseid):
    r3 = session.get(course_lectures_url % (courseid))
    if 'results' not in r3.json():
        print("Error: Course not found")
        exit(0)
    lectures = [item for item in r3.json()['results'] if item['_class'] == 'lecture']
    return lectures


def get_assets_of_lecture(session, courseid, lecture):
    if (str(courseid) + '_' + str(lecture['id']) in downloaded_lectures):
        print("Already downloaded this lecture (%s). Skipping..." % (str(lecture['id'])))
        return

    if not os.path.isdir(download_dir):
        os.makedirs(download_dir)
    course_dir = os.path.join(download_dir,
                              clean_string(
                                  str(selected_course['id']) + '_' + '-'.join(selected_course['title'].split(' '))))
    if not os.path.isdir(course_dir):
        os.makedirs(course_dir)
    if len(lecture['supplementary_assets']) > 0:
        print('%s has %d supplementary asset' % (lecture['title'], len(lecture['supplementary_assets'])))
        for a in lecture['supplementary_assets']:
            download_asset(session, courseid, lecture['id'], a)
    r4 = session.get(assets_of_lecture_url % (courseid, lecture['id']))
    try:
        asset = r4.json()['asset']
    except:
        print(r4)

    if (asset['asset_type'] == 'Video'):
        url = asset['stream_urls']['Video'][0]['file']
        ext = url.split('/')[-1].split('?')[0].split('.')[-1]
        vid_name = clean_string(str(lecture['id']) + '_' + '-'.join(lecture['title'].split(' ')))
        vid_filename = vid_name + '.' + ext
        filename = os.path.join(course_dir, vid_filename)
        print("Downloading video: %s" % (vid_filename))
        vid = session.get(url)
        with open(filename, 'wb') as f:
            f.write(vid.content)
    downloaded_lectures.append(str(courseid) + '_' + str(lecture['id']))


def download_asset(session, courseid, lectureid, asset):
    print("Downloading file: ", asset['filename'], "...")
    r = session.get(download_asset_url % (courseid, lectureid, asset['id']))
    filename, ext = tuple(asset['filename'].rsplit('.', 1))
    if not os.path.isdir(download_dir):
        os.makedirs(download_dir)
    course_dir = os.path.join(download_dir,
                              clean_string(
                                  str(selected_course['id']) + '_' + '-'.join(selected_course['title'].split(' '))))
    filepath = os.path.join(course_dir, clean_string(str(lectureid) + '_' + filename) + '.' + ext)

    try:
        urls = r.json()['download_urls']
        content = session.get(urls['File'][0]['file'])
        print("URL: ", urls['File'][0]['file'])
        open(filepath, 'wb').write(content.content)
    except:
        print(r)

    # print("Saved: ", asset['filename'])


def download_all_from_course(session):
    print("Course: %s" % (selected_course['id']))
    if selected_course_id in downloaded_courses:
        print("Already downloaded this course. Skipping...")
        return
    print("Downloading all lectures and assets...")
    lectures = get_lectures_of_course(session, selected_course_id)
    for l in lectures:
        get_assets_of_lecture(session, selected_course_id, l)
    downloaded_courses.append(selected_course_id)
    persist_internal_state()


def download_single_lecture_from_course(session, lecture):
    print("Downloading lecture: %s" % (lecture['title']))
    get_assets_of_lecture(session, selected_course_id, lecture)


def cmd_download(session, args_list):
    assert len(args_list) == 1
    download_all = args_list[0].lower() == 'all'
    if download_all:
        print('''
        -------------------------
        | DOWNLOAD ALL LECTURES |
        -------------------------
        ''')
        download_all_from_course(session)
        print("Successfully downloaded all lectures!")
    else:
        found = False
        for l in lectures_of_selected_course:
            if int(l['id']) == int(args_list[0]):
                found = True
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


def cmd_select_course(session, args_list):
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
    print("Type 'download all' or 'download <LectureID> to save videos and assets to your computer")


def cmd_downloadall(session, args_list):
    global enrolled_courses
    for c in enrolled_courses:
        cmd_select_course(session, [c['id']])
        cmd_download(session, ['all'])


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
    pickle.dump((downloaded_courses, downloaded_lectures), istate_file)
    istate_file.close()


def greeting():
    print('''
    ===========================
    ||                       ||
    || UDEMY DOWNLOADER V1.0 ||
    ||       Andy Tran       ||
    ===========================
    ''')


def clean_string(path):
    return re.sub('[^\d\w\-_]+', '', path)


greeting()
host = input("Udemy Server (default www.udemy.com):")
build_env(host)
login(session)
get_enrolled_courses(session)
loop_user_interaction(session)
