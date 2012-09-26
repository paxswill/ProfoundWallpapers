#!/usr/bin/env python3
from urllib.request import urlopen
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import random
import re
import os
import os.path
import subprocess
import argparse

class Feed:
    def __init__(self, feed_url):
        self.url = feed_url
        self.feed = BeautifulSoup(urlopen(feed_url), "xml")

    def top(self):
        if self.feed.contents[0] == 'rss':
            return self.feed.item
        elif self.feed.contents[0] == 'feed':
            return self.feed.entry

    def random(self):
        if self.feed.contents[0] == 'rss':
            children = self.feed.find_all('items')
        elif self.feed.contents[0] == 'feed':
            children = self.feed.find_all('entry')
        return random.choice(children)

class Tumblr(Feed):
    def __init__(self, tumblr_name):
        self.url = "http://{}.tumblr.com/api/read?type=photo".format(tumblr_name)
        self.feed = BeautifulSoup(urlopen(tumblr_url), 'xml')

    def __len__(self):
        return int(self.feed.posts['total'])

    def __getitem__(self, key):
        # Screw slices (at least for now)
        # Support negative indicies
        if key < 0:
            key = len(self) + key
        # Catch out of bounds indices
        if key < 0 or key > len(self):
            raise TypeError("post index out of range")
        # items 0-20 are cached in the initial request
        if key < 20:
            return self.feed('post')[key]
        else:
            focused_url = "{0.s}&start={}&num=1".format(self.url, post_index)
            restricted = BeautifulSoup(urlopen(focused_url), 'xml')
            return restricted.post

    def __iter__(self):
        # Start with the cached 20
        for index in range(20 if len(self) > 20 else len(self)):
            yield self[index]
        # Now go in jumps of 50 towards the end
        for jump in range(20, len(self), 50):
            window_url = "{}&start={}&num=50".format(self.url, self.jump)
            window = BeautifulSoup(urlopen(window_url), 'xml')
            for post in window('post'):
                yield post

    def __reversed__(self):
        pass

    def top(self):
        return self[0]

    def random(self):
        return random.choice(self)

class ProfoundProgrammer(Tumblr):
    # Cache the Regexes
    nsfw_regex = re.compile("HD Version")
    sfw_regex = re.compile("HD Safe-For-Work Version")

    def __init__(self, safe_for_work=False):
        super().__init__('theprofoundprogrammer')
        self.sfw = safe_for_work

    def _filter_hd(self, tag):
        if tag.description:
            if self.sfw:
                return self.sfw_regex.search(tag.description.text)
            else:
                return self.nsfw_regex.search(tag.description.text)
        else:
            return False

    def pick_top(self):
        return self.feed.find(self._filter_hd).description.text

    def pick_random(self):
        return random.choice(self.feed(self._filter_hd)).description.text

    def extract(self, element):
        soup = BeautifulSoup(element)
        if self.sfw:
            hd_url = soup.find(name='a', text=self.sfw_regex, href=True)
        else:
            hd_url = soup.find(name='a', text=self.nsfw_regex, href=True)
        return hd_url['href']

    def top(self):
        return self.extract(self.pick_top())

    def random(self):
        return self.extract(self.pick_random())

def download(image_url, target='~/Pictures/Profound Programmer/'):
    # Create a destination for our images
    target_dir = os.path.expanduser(target)
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    elif not os.path.exists(target_dir):
        print("Really, you created a plain file where I'm trying to save \
                stuff?")
        return
    # Figure out what to call our new image
    image_name = urlparse(image_url).path.split('/')[-1:][0]
    destination = os.path.join(target_dir, image_name)
    # Don't download it again if we already have it
    if not os.path.exists(destination):
        with urlopen(image_url) as request, open(destination, 'wb') as image:
            image.write(request.read())
    return destination

def set_background(image_path):
    applescript = \
        "tell application \"Finder\" to set desktop picture to POSIX file \"{}\""
    command = ["/usr/bin/osascript", "-e"]
    command.append(applescript.format(image_path))
    subprocess.call(command)

if __name__ == '__main__':
    # Build up an argument parser
    parser = argparse.ArgumentParser(description=
        "Desktop updater of images sourced from theprofoundprogrammer.com")
    # Options controlling safe-for-work-ness
    sfw = parser.add_mutually_exclusive_group()
    sfw.add_argument("-s", "--sfw", help="Only show safe for work versions",
            action="store_true")
    sfw.add_argument("-n", "--nsfw", help="Show all HD versions (Default).",
            action="store_false")
    # Options controlling which image to pick
    which = parser.add_mutually_exclusive_group()
    which.add_argument("-r", "--random", help="Pick a random image.",
            action="store_true")
    which.add_argument("-t", "--top",
            help="Pick the most recent image (Default).", action="store_true")
    # Figure out where to put the images
    parser.add_argument("target", nargs='?', default="~/Pictures/Profound Programmer/",
            help="Where to save the images to.")
    # Parse away
    parser.set_defaults(nsfw=True, top=True)
    args = parser.parse_args()
    source = ProfoundProgrammer(args.sfw)
    if args.random:
        image_url = source.random()
    else:
        image_url = source.top()
    image_path = download(image_url, args.target)
    set_background(image_path)

