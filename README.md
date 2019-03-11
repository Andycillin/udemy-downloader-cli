# Udemy Downloader CLI
Mini script for downloading Videos & Assets from Udemy and Udemy Business

Version 1.3 

Author: Andy Tran  

Sourcecode: [Github](https://github.com/Andycillin/udemy-downloader-cli)

## Features:
- Supports both Udemy and Udemy Business
- Login once
- List all enrolled courses and download 'em all 
- Download a single course of choice
- Download a single lecture of choice
- All supplementaries belonging to the lecture will be included in download

## Usage:
```bash
python udemy_downloader.py [options]
```
#### Options: 
| Options | Description  |
| -------------------------------------- |------------- |
| `-s` <br/>  `--server` &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;| Set udemy server address, default is www.udemy.com (You may need this if you are using Udemy for Business) |
| `-n` <br/> `--new_user`| Login using another account      |
| `-l` <br/> `--showlog` | Print all logs      |

## Command list:
List all enrolled courses
```bash
> list
```

Download all enrolled courses 
```bash
> downloadall
```

Select a course and list all lectures
```bash
> select <Course ID>
```

Download all assets from selected course
```bash
> download all
```

Download a single lecture and its assets 
```bash
> download <Lecture ID>
```



## License
UdemyDownloaderCLI is MIT licensed
