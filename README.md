# Udemy Downloader CLI
Mini script for downloading Videos & Assets from Udemy and Udemy Business

Author: Andy Tran  

Sourcecode: [Github](https://github.com/Andycillin/udemy-downloader-cli)

Usage:
```bash
python udemy_downloader.py [options]
```
Options: 
- -s, --server : Set udemy server address, default is www.udemy.com (You may need this if you are using Udemy for Business)
- -n, --new_user : Login with new account
- -l, --showlog : Print all logs
 

Command list:
```bash
> list
```
List all enrolled courses

```bash
> downloadall
```
Download all enrolled courses 

```bash
> select <Course ID>
```
Select a course and list all lectures

```bash
> download all
```
Download all assets from selected course

```bash
> download <Lecture ID>
```
Download a single lecture and its assets 



## License
UdemyDownloaderCLI is MIT licensed