#!/usr/bin/env python3

import argparse
import os
import os.path
import random
import re
import subprocess
import platform
# Python 2.x Workaround
if int(platform.python_version_tuple()[0]) < 3:
    from urllib2 import urlopen
    from urlparse import urlparse
else:
    from urllib.request import urlopen
    from urllib.parse import urlparse

from bs4 import BeautifulSoup


class Feed(object):
    def __init__(self, feed_url):
        self.url = feed_url
        request = urlopen(feed_url)
        self.feed = BeautifulSoup(request, "xml")
        request.close()

    def _atom(self):
        return self.feed.contents[0] == 'feed'

    def _rss(self):
        return self.feed.contents[0] == 'rss'

    def _posts(self):
        if self._rss():
            return self.feed('item')
        elif self._atom():
            return self.feed('event')

    def __len__(self):
        return len(self._posts())

    def __getitem__(self, key):
        return self._posts()[key]

    def __iter__(self):
        return iter(self._posts())

    def extract(self, post):
        if self._rss():
            return post.link.text
        elif self._atom():
            return post.find(name='link', rel=False)

    def top(self):
        for post in self:
            image = self.extract(post)
            if image:
                return image
        else:
            return None

    def random(self):
        image = None
        watchdog = 0
        while image is None and watchdog < (len(self) * 1.5):
            image = self.extract(random.choice(self))
            watchdog += 1
        return image


class Tumblr(Feed):
    def __init__(self, tumblr_name):
        Feed.__init__(self, "http://{}.tumblr.com/api/read?type=photo".format(
            tumblr_name))

    def __len__(self):
        return int(self.feed.posts['total'])

    def __getitem__(self, key):
        # Screw slices (at least for now)
        # Support negative indicies
        if key < 0:
            key = len(self) + key
        # Catch out of bounds indices
        if key < 0 or key > len(self):
            raise IndexError("post index out of range")
        # items 0-20 are cached in the initial request
        if key < 20:
            return self.feed('post')[key]
        else:
            focused_url = "{}&start={}&num=1".format(self.url, key)
            focused = BeautifulSoup(urlopen(focused_url), 'xml')
            return focused.post

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

    def extract(self, post):
        photos = post('photo-url')
        photo = max(photos, 'max-width')
        return photo.text


class ProfoundProgrammer(Tumblr):
    # Cache the Regexes
    nsfw_regex = re.compile("HD Version")
    sfw_regex = re.compile("HD Safe-For-Work Version")

    def __init__(self, safe_for_work=False):
        Tumblr.__init__(self, 'theprofoundprogrammer')
        self.sfw = safe_for_work

    def extract(self, post):
        soup = BeautifulSoup(post.find('photo-caption').text)
        hd_url = None
        if self.sfw:
            hd_url = soup.find(name='a', text=self.sfw_regex, href=True)
        if hd_url is None:
            hd_url = soup.find(name='a', text=self.nsfw_regex, href=True)
        if hd_url:
            return hd_url['href']
        else:
            return None


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
        request = urlopen(image_url)
        with open(destination, 'wb') as image:
            image.write(request.read())
        request.close()
    return destination


def set_background(image_path):
    if platform.system() == 'Darwin':
        #OS X
        applescript = "tell application \"Finder\" to set desktop picture to \
                POSIX file \"{}\""
        command = ["/usr/bin/osascript", "-e"]
        command.append(applescript.format(image_path))
    else:
        dt_save = subprocess.check_output(['/usr/bin/xprop', '-root',
                                           '_DT_SAVE_MODE'])
        dt_save = dt_save.decode()
        if dt_save == 'xfce4' or os.environ['DESKTOP_SESSION'] == 'xfce':
            # Xfce
            command = ["/usr/bin/xfconf-query", "-c", "xfce4-desktop", "-p",
                       "/backdrop/screen0/monitor0/image-path", "-s",
                       image_path]
        elif os.environ['KDE_FULL_SESSION'] == 'true':
            # KDE
            pass
        elif os.environ['XDG_CURRENT_DESKTOP'] == 'unity':
            command = ['usr/bin/gsettings', 'set',
                       'org.gnome.desktop.background', 'picture-uri',
                       image_path]
        elif 'GNOME_DESKTOP_SESSION_ID' in os.environ:
            # Some sort of Gnome
            gnome_version = subprocess.check_output(['/usr/bin/gnome-session',
                                                     '--version'])
            gnome_version = gnome_version.decode()
            if re.match(re.compile('3'), gnome_version):
                command = ['usr/bin/gsettings', 'set',
                           'org.gnome.desktop.background', 'picture-uri',
                           image_path]
            elif re.match(re.compile('2'), gnome_version):
                command = ['/usr/bin/gconftool-2', '-t', 'str', '--set',
                           '/desktop/gnome/background/picture_filename',
                           image_path]
    subprocess.call(command)


if __name__ == '__main__':
    # Build up an argument parser
    parser = argparse.ArgumentParser(description=
            "Desktop updater of images sourced from theprofoundprogrammer.com")
    # Options controlling safe-for-work-ness
    sfw = parser.add_mutually_exclusive_group()
    sfw.add_argument("-s", "--sfw", action="store_true",
                     help="Prefer safe for work versions")
    sfw.add_argument("-n", "--nsfw", action="store_false",
                     help="Prefer not safe for work versions (Default).")
    # Options controlling which image to pick
    which = parser.add_mutually_exclusive_group()
    which.add_argument("-r", "--random", action="store_true",
                       help="Pick a random image.")
    which.add_argument("-t", "--top", action="store_true",
                       help="Pick the most recent image (Default).")
    # Figure out where to put the images
    parser.add_argument("target", default="~/Pictures/Profound Programmer/",
                        help="Where to save the images to.", nargs='?')
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
