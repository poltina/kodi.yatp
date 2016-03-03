# coding: utf-8
# Module: actions
# Created on: 27.07.2015
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)
# Licence: GPL v.3: http://www.gnu.org/copyleft/gpl.html

import os
import xbmcgui
from xbmc import LOGNOTICE
from libs.simpleplugin import Plugin
import json_requests as jsonrq
from buffering import buffer_torrent, stream_torrent, add_torrent, get_videofiles

plugin = Plugin()
string = plugin.get_localized_string
icons = os.path.join(plugin.path, 'resources', 'icons')
commands = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'commands.py')


def _play(path):
    """
    Play a videofile

    :param path:
    :return:
    """
    plugin.log('Path to play: {0}'.format(path), LOGNOTICE)
    success = True if path else False
    return plugin.resolve_url(path, succeeded=success)


def root(params):
    """
    Plugin root

    :param params:
    :return:
    """
    return [{'label': string(32000),
             'thumb': os.path.join(icons, 'play.png'),
             'url': plugin.get_url(action='select_torrent', target='play')},
            {'label': string(32001),
             'thumb': os.path.join(icons, 'down.png'),
             'url': plugin.get_url(action='select_torrent', target='download'),
             'is_folder': False},
            {'label': string(32002),
             'thumb': plugin.icon,
             'url': plugin.get_url(action='torrents')}]


def select_torrent(params):
    """
    Select .torrent file to play

    :param params:
    :return:
    """
    torrent = xbmcgui.Dialog().browse(1, string(32003), 'video', mask='.torrent')
    if torrent:
        plugin.log('Torrent selected: {0}'.format(torrent), LOGNOTICE)
        if params['target'] == 'play':
            return list_files({'torrent': torrent})
        else:
            download_torrent({'torrent': torrent})


def play_torrent(params):
    """
    Play torrent

    :param params:
    :return:
    """
    file_index = params.get('file_index')
    if file_index is not None and file_index != 'dialog':
        file_index = int(file_index)
    return _play(buffer_torrent(params['torrent'], file_index))


def play_file(params):
    """
    Stream a file from torrent by its index

    The torrent must be already added to the session!

    :param params:
    :return:
    """
    return _play(stream_torrent(int(params['file_index']), params['info_hash']))


def download_torrent(params):
    """
    Add torrent for downloading

    :param params:
    :return:
    """
    download_dir = params.get('download_dir') or plugin.download_dir
    jsonrq.download_torrent(params['torrent'], download_dir)
    xbmcgui.Dialog().notification('YATP', string(32004), plugin.icon, 3000)


def torrents(params):
    """
    Display the list of torrents in the session

    :param params:
    :return:
    """
    listing = []
    torrent_list = sorted(jsonrq.get_all_torrent_info(), key=lambda i: i['added_time'], reverse=True)
    for torrent in torrent_list:
        if torrent['state'] == 'downloading':
            label = u'[COLOR=red]{0}[/COLOR]'.format(torrent['name'])
        elif torrent['state'] == 'seeding':
            label = u'[COLOR=green]{0}[/COLOR]'.format(torrent['name'])
        elif torrent['state'] == 'paused':
            label = u'[COLOR=gray]{0}[/COLOR]'.format(torrent['name'])
        else:
            label = u'[COLOR=blue]{0}[/COLOR]'.format(torrent['name'])
        item = {'label': label,
                'url': plugin.get_url(action='show_files', info_hash=torrent['info_hash']),
                'is_folder': True}
        if torrent['state'] == 'downloading':
            item['thumb'] = os.path.join(icons, 'down.png')
        elif torrent['state'] == 'seeding':
            item['thumb'] = os.path.join(icons, 'up.png')
        elif torrent['state'] == 'paused':
            item['thumb'] = os.path.join(icons, 'pause.png')
        else:
            item['thumb'] = os.path.join(icons, 'question.png')
        listing.append(item)
        context_menu = [(string(32005),
                         'RunScript({commands},pause_all)'.format(commands=commands)),
                        (string(32006),
                        'RunScript({commands},resume_all)'.format(commands=commands)),
                        (string(32007),
                         'RunScript({commands},delete,{info_hash})'.format(commands=commands,
                                                                           info_hash=torrent['info_hash'])),
                        (string(32008),
                         'RunScript({commands},delete_with_files,{info_hash})'.format(commands=commands,
                                                                                      info_hash=torrent['info_hash'])),
                        (string(32066),
                         'RunScript({commands},restore_finished,{info_hash})'.format(commands=commands,
                                                                                      info_hash=torrent['info_hash'])),
                        (string(32065),
                         'RunScript({commands},show_info,{info_hash})'.format(commands=commands,
                                                                                      info_hash=torrent['info_hash'])),
                        ]
        if torrent['state'] == 'paused':
            context_menu.insert(0, (string(32009),
                                    'RunScript({commands},resume,{info_hash})'.format(commands=commands,
                                                                                      info_hash=torrent['info_hash'])))
        else:
            context_menu.insert(0, (string(32010),
                                    'RunScript({commands},pause,{info_hash})'.format(commands=commands,
                                                                                      info_hash=torrent['info_hash'])))
        item['context_menu'] = (context_menu, True)
    return listing


def list_files(params):
    """
    Add a torrent to the sessiona and display the list of files in a torrent

    :param params:
    :return:
    """
    torrent_data = add_torrent(params['torrent'])
    if torrent_data is not None:
        return _build_file_list(torrent_data['files'], torrent_data['info_hash'])
    else:
        xbmcgui.Dialog().notification(plugin.id, string(32023), plugin.icon, 3000)
    return []


def show_files(params):
    """
    Display the list of videofiles

    :param params:
    :return:
    """
    return _build_file_list(jsonrq.get_files(params['info_hash']), params['info_hash'])


def _build_file_list(files, info_hash):
    """
    Create the list of videofiles in a torrent

    :param files:
    :param info_hash:
    :return:
    """
    videofiles = get_videofiles(files)
    listing = []
    for file_ in videofiles:
        ext = os.path.splitext(file_[1].lower())[1]
        if ext == '.avi':
            thumb = os.path.join(icons, 'avi.png')
        elif ext == '.mp4':
            thumb = os.path.join(icons, 'mp4.png')
        elif ext == '.mkv':
            thumb = os.path.join(icons, 'mkv.png')
        elif ext == '.mov':
            thumb = os.path.join(icons, 'mov.png')
        else:
            thumb = os.path.join(icons, 'play.png')
        listing.append({'label': '{name} [{size}{unit}]'.format(name=file_[1].encode('utf-8'),
                                                                size=file_[2] / 1048576,
                                                                unit=string(32067)),
                        'thumb': thumb,
                        'url': plugin.get_url(action='play_file',
                                              info_hash=info_hash,
                                              file_index=file_[0]),
                        'is_playable': True
                        })
    return plugin.create_listing(listing, cache_to_disk=True)


# Map actions
plugin.actions['root'] = root
plugin.actions['select_torrent'] = select_torrent
plugin.actions['play'] = play_torrent
plugin.actions['play_file'] = play_file
plugin.actions['download'] = download_torrent
plugin.actions['torrents'] = torrents
plugin.actions['list_files'] = list_files
plugin.actions['show_files'] = show_files
