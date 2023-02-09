import os
import praw
import pprint
import youtube_dl
from moviepy.editor import *
import moviepy.video.fx.all as vfx
from moviepy.video.tools.segmenting import findObjects
from datetime import datetime
pp = pprint.PrettyPrinter(width=41, compact=True)

# define asset paths
BG_PATH = './assets/bg.mp4'
INTRO_PATH = './assets/intro.mp4'
VSEG_PATH = './assets/vseg.png'
HSEG_PATH = './assets/hseg.png'
TRANSITION_PATH = './assets/transition.mp4'

# define base paths
OUT_BASE_PATH = './out/'
SCRAPED_BASE_PATH = './scraped/'
COMPS_BASE_PATH = './out/comps/'

BASE_PATHS = [
    OUT_BASE_PATH,
    SCRAPED_BASE_PATH,
    COMPS_BASE_PATH
]

# TODO git rm -rf /assets/ and re add the files
# TODO detect if there is no audio in either a clip or the video as a whole and add royalty free music over it
# TODO possibly multithread each source
# TODO upload to youtube if automatic quality checks are met
# TODO possibly be able to set each individual queue job with its own transitions, intro, etc
# TODO add in more segmentation options, detect video aspect ratio and make from there
# TODO research more suitable video sources
# TODO Implement compilation thumbnail generation
# TODO allow pagination of reddit results/cursor
# justguysbeingdudes whywomenlivelonger

def mkDir(path):
    if not os.path.exists(path):
        os.mkdir(path)


def generateJobPathName(source):
    dt = str(datetime.now())[0:10]
    return f'{source} - {dt}/'


def generateBasePaths():
    for path in BASE_PATHS:
        mkDir(path)


def generateJobPaths(source):
    folderName = generateJobPathName(source)
    print('making job folders: ', folderName)

    scraped = os.path.join(SCRAPED_BASE_PATH, folderName)
    comps = os.path.join(COMPS_BASE_PATH, folderName)
    job_paths = [scraped, comps]

    for path in job_paths:
        mkDir(path)

    return job_paths


def makeCompsFromDir(dir, out):
    for i, file in enumerate(os.listdir(dir)):
        f = os.path.join(dir, file)
        if (os.path.isfile(f)):
            print('now compositing:', f)
            compositeVideo(f, str(out + str(i) + '.mp4'))


def scrapeVideosFromTwitch(channel, timeframe, limit):
    # TODO add twitch scraping support
    print('scraping {} clips from twitch channel {}'.format(limit, channel))


def scrapeVideosFromReddit(subreddit, timeframe, limit):
    userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0"
    reddit = praw.Reddit(
        client_id="tNdSMBEZgmVC8LHyyKlNlA",
        client_secret="fZPKOZOhImYxKT78TLbGV3kFDCQhGg",
        user_agent=userAgent
    )

    video_posts = []
    for submission in reddit.subreddit(subreddit).top(time_filter=timeframe, limit=limit):
        if (submission.media and 'reddit_video' in submission.media):
            video_posts.append(submission.url)
    return video_posts


def loopClipToDuration(clip, duration):
    return vfx.loop(clip).set_duration(duration)


def getSegmentationPath(w, h):
    if w > h:
        return ImageClip(HSEG_PATH)
    else:
        return ImageClip(VSEG_PATH)


def downloadVideos(urls, basePath, format='mp4', fileName='%(title)s.%(ext)s'):
    ydlOpts = {
        # the format that it can be
        'format': ('bestvideo[ext='+format+']+bestaudio[ext=m4a]/'+format),
        # makes it so that if the link is in a youtube playlist it wont download the whole playlist
        'noplaylist': 'true',
        'outtmpl': basePath+fileName,  # output location and name
        'ignoreerrors': 'true',  # if error move one
        'restrictfilenames': 'true',  # gets rid of spaces in output name
        'getTitle': 'true',
    }

    with youtube_dl.YoutubeDL(ydlOpts) as ydl:
        ydl.download(urls)


def saveVideo(clip, out, threads=8, fps=24, codec='h264_nvenc', bitrate='12M', preset='fast'):
    clip.write_videofile(
        out, threads=threads, fps=fps, codec=codec, bitrate=bitrate, preset=preset)


def arrangeCompilation(transition, compDir, intro, out):
    comps = []
    for file in os.listdir(compDir):
        f = os.path.join(compDir, file)
        if (os.path.isfile(f)):
            print('adding comp to list')
            comps.append(transition)
            comps.append(VideoFileClip(f))

    comps.insert(0, intro)
    vid = concatenate_videoclips(comps)
    saveVideo(vid, out)


def compositeVideo(clipPath, out, threads=8, fps=24, codec='h264_nvenc', bitrate='12M', preset='fast'):
    clip = VideoFileClip(clipPath)
    bg = loopClipToDuration(VideoFileClip(BG_PATH), clip.duration)
    template = getSegmentationPath(clip.w, clip.h)
    regions = findObjects(template)

    comp = [c.resize(r.size)
            .set_mask(r.mask)
            .set_pos(r.screenpos)
            for c, r in zip([bg, clip], regions)]

    saveVideo(CompositeVideoClip(comp, template.size), out)


if __name__ == '__main__':
    generateBasePaths()
    timeframe = 'year'
    limit = 60
    sources = ['startledcats', 'perfectlycutscreams', 'tiktokcringe', 'fixedbytheduet']
    transition = VideoFileClip(TRANSITION_PATH)
    intro = VideoFileClip(INTRO_PATH)

    for source in sources:
        scraped, comps = generateJobPaths(source)
        videos = scrapeVideosFromReddit(source, timeframe, limit)
        downloadVideos(videos, scraped)
        makeCompsFromDir(scraped, comps)
        arrangeCompilation(transition, comps, intro,
                           os.path.join(OUT_BASE_PATH, f'{source}.mp4'))
