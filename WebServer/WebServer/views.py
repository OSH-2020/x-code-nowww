from django.http import JsonResponse
from django.shortcuts import render
from py2neo import *
from GDBFS import neobase, UsrInputConv
import os
import tkinter as tk
from tkinter import filedialog
from . import settings


def home(request):
    return render(request, 'home.html')


def gdbfs(request):
    try:
        if type(settings.fuse_process) == settings.FuseProcess:
            settings.fuse_process.terminate()
            os.system("umount {}".format(settings.fuse_process.mount_path))
    except AttributeError:
        pass
    settings.fuse_process = settings.FuseProcess(request.POST.get('path'))
    settings.fuse_process.start()
    return render(request, 'gdbfs.html')


def find_files(request):
    description = request.POST.get("description")
    ctime = request.POST.get("ctime")
    atime = request.POST.get("atime")
    mtime = request.POST.get("mtime")
    # Get usr's input -- Gao
    l_grammared = UsrInputConv.add_grammar(
        UsrInputConv.pos_tag(
            UsrInputConv.tree_flatting(
                UsrInputConv.ne_chunk(
                    UsrInputConv.pos_tag(
                        UsrInputConv.word_tokenize(description))))))
    l_filtered = UsrInputConv.list_filter(UsrInputConv.pos_tag(l_grammared))
    atime_period = UsrInputConv.time_top(atime)
    ctime_period = UsrInputConv.time_top(ctime)
    mtime_period = UsrInputConv.time_top(mtime)
    search_key = UsrInputConv.KeyWord(l_filtered, atime_period, ctime_period, mtime_period)
    print('keywords: ', search_key.keywords)
    print("acmtime", search_key.atime, search_key.ctime, search_key.mtime, sep=', ')

    # Get files according to keywords and file_properties -- Wang
    graph = Graph("bolt://localhost:7687")
    result = neobase.get_files(graph,
                               keywords=search_key.keywords,
                               file_properties={'cTime': search_key.ctime,
                                                'aTime': search_key.atime,
                                                'mTime': search_key.mtime})
    if len(result) == 0:
        return JsonResponse({"nodes": [], "edges": []})

    nodes = []
    node_indexes = {}
    edges = []
    node_count = 0
    for file_node in result:
        file_node_as_dict = {'name': file_node.node['name'], 'label': 'File'}
        file_node_as_dict.update(file_node.node)
        file_node_as_dict['keywords'] = list(file_node.keywords)
        nodes.append(file_node_as_dict)
        node_indexes[file_node.node['path']] = node_count
        node_count += 1
        for keyword in file_node.keywords:
            if {'name': keyword, 'label': 'Keyword'} not in nodes:
                nodes.append({'name': keyword, 'label': 'Keyword'})
                node_indexes[keyword] = node_count
                node_count += 1
            edges.append({'source': node_indexes[file_node.node['path']],
                          'target': node_indexes[keyword],
                          'relation': 'TO',
                          'value': 1})

    name_dict = {"nodes": nodes, "edges": edges}
    from pprint import pprint
    pprint(nodes)
    pprint(edges)
    return JsonResponse(name_dict)


def open_file(request):
    path = request.POST.get('path')
    path = neobase.convert_path(path,
                                settings.fuse_process.fuse_obj.root,
                                settings.fuse_process.fuse_obj.mount_point)
    ok = True
    if not os.access(path, os.F_OK):
        ok = False
    os.system("nohup xdg-open {}".format(path))
    return JsonResponse({'ok': ok})


def rm_file(request):
    path = request.POST.get('path')
    path = neobase.convert_path(path,
                                settings.fuse_process.fuse_obj.root,
                                settings.fuse_process.fuse_obj.mount_point)
    os.system("rm {}".format(path))
    return JsonResponse({'path': path})


def choose_dir(request):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askdirectory()
    root.destroy()
    print(path)
    return JsonResponse({'path': path})


def add_files(request):
    root = tk.Tk()
    root.withdraw()
    paths = filedialog.askopenfilenames()
    root.destroy()
    for path in paths:
        os.system('cp {} {}'.format(path, settings.fuse_process.fuse_obj.mount_point))
    return JsonResponse({'path': paths})


def umount(request):
    try:
        if type(settings.fuse_process) == settings.FuseProcess:
            settings.fuse_process.terminate()
            os.system("umount {}".format(settings.fuse_process.mount_path))
    except AttributeError:
        pass
    return render(request, 'home.html')
