import os

for root, dirs, files in os.walk("/home/brumeako/Projects"):
    for directory in dirs:
        if directory == ".git":
            print(f"{root}/{directory}")