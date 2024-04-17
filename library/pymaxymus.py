'''
Library for data loading and analysis from the MAXYMUS microscope at BESSY

authors: Kathinka Gerlinger, Michael Schneider, Max Born Institute Berlin
date: 01.2020
'''

import pandas as pd
import numpy as np
import imageio
import matplotlib.pyplot as plt
import os, sys
import re
from matplotlib_scalebar.scalebar import ScaleBar
from mpl_toolkits.axes_grid1 import make_axes_locatable
import pyparsing as pp


##################################################################################################################

#                     IMPORT DATA

##################################################################################################################

def import_single(fname):
    '''
    Import a single image recorded at the MAXYMUS microscope at BESSY.
    INPUT:
        filename including path
    OUTPUT:
        np.array of the data
    KG, 01.2020
    '''
    data = pd.read_csv(fname, sep = '\t', header = None)
    data = np.array(data)
    if np.isnan(data[0,-1]): #in the file, KG used as example, the last column contained NaN.
        return data[:, :-1]
    return data

def import_bbx(fname):
    '''
    Import the time resolved data recorded at the MAXYMUS microscope at BESSY.
    INPUT:
        fname: filename to load
    OUTPUT:
        np.array of the data with dimensions [time, x, y]
    KG, MS 01.2020
    '''
    imagedata = np.fromfile(fname, dtype='>i4')
    imagedata = np.bitwise_and(imagedata, 0x7FFFF)
    dim_t, dim_x, dim_y = imagedata[:3]
    return np.reshape(imagedata[3:], (dim_t, dim_y, dim_x))

def parse_header(fname):
    '''
    Parses the separate header files (*.hdr) and returns a nested dict.
    '''
    EQ, LBRACE, RBRACE, LPAR, RPAR, COMMA, SEMICOLON = map(pp.Suppress, '={}(),;')

    value = pp.Forward()  # this tells pyparsing that values can be recursive
    listvalue = pp.Forward()

    name = pp.Word(pp.alphanums + '_')
    entry = pp.Group(name + EQ + value + SEMICOLON)  # this is the basic name-value pair

    strings = pp.quotedString.setParseAction(pp.removeQuotes)
    numbers = pp.Word(pp.nums + '.-').setParseAction(lambda n: float(n[0]))
    listcount = pp.Word(pp.nums).suppress()

    dict_entry = pp.Dict(LBRACE + pp.OneOrMore(entry) + RBRACE)
    list_entry = pp.Group(LPAR + listcount + COMMA + pp.delimitedList(listvalue) + RPAR)

    listvalue << (dict_entry | numbers)
    value << (dict_entry | list_entry | numbers | strings)
    
    result = entry.parseFile(fname)
    return result[0].asDict()
    

def import_header(fname, fsave):
    '''
    Import the header for data recorded at the MAXYMUS microscope at BESSY.
    INPUT:
        fname: filename to load
        fsave: filname to save the header data in a hdf file
    OUTPUT:
        Pandas DataFrame with the dwelltime, x-range, x-step numbers, y-range and y-step numbers
    KG, MS 01.2020
    '''
    file = open(fname, 'r')
    header = file.readlines()
    
    next_line_x = False
    next_line_y = False
    for text in header:
        if 'ScanDefinition' in text:
            dwelltime = get_number('Dwell', text)
        if 'PAxis' in text:
            x_min = get_number('Min', text)
            x_max = get_number('Max', text)
            next_line_x = True
            continue
        if next_line_x:
            x_points = get_number('Points', text)
            next_line_x = False
        if 'QAxis' in text:
            y_min = get_number('Min', text)
            y_max = get_number('Max', text)
            next_line_y = True
            continue
        if next_line_y:
            y_points = get_number('Points', text)
            next_line_y = False
            
    df = pd.DataFrame({'Dwelltime': [dwelltime], 'X-range': [np.abs(x_max - x_min)], 'X-steps': [x_points],
                   'Y-range': [np.abs(y_max - y_min)], 'Y-steps': [y_points]})
    df.to_hdf(fsave, key = 'header', mode = 'w')
    return df

def get_number(keyword, text):
    match = re.search(keyword + r' = (.*?);(.*)', text)
    if match:
        number = match.group(1)
        if np.logical_and(not number[0].isdigit(), number[0]!='-'):
            nnumber = ''
            for i in number[1:]:
                if np.logical_or(i.isdigit(), np.logical_or(i == '-', i == '.')):
                    nnumber += i
                elif i == ',':
                    break
            number = np.float(nnumber)
        elif not number[-1].isdigit():
            number = np.float(number[:-1])
        else:
            number = np.float(number)
        return number
    else:
        print('Keyword not found in text.')
    return None



##################################################################################################################

#                     TIME RESOLVED DATA SORTING AND NORMALIZING

##################################################################################################################

def sort_time(data, magic_number):
    '''
    Sort the data returned by import_bbx(). Due to the measurement scheme,
    the difference between pump and probe is not sorted in the timeline.
    We need to sort it manually, using the so called magic number as a
    reference. The frame order for magic_number=20 is [0, 20, 40, ..., 1980,
    2000, 19, 39, 59, ...]
    INPUT:
        data: unsorted np.array as returned by import_bbx()
        magic_number: is the magic number of the time resolution
    OUTPUT:
        sorted np.array
    KG, MS 01.2020
    '''
    t_index = np.arange(data.shape[0], dtype=int)
    sort_index = (t_index * magic_number) % data.shape[0]
    return data[np.argsort(sort_index)]

def normalize(data, XMCD, tlim = np.s_[:], xlim = np.s_[:], ylim = np.s_[:], axis = 0):
    '''
    Normalize each data point over time (i.e. every pixel is divided by the
    mean of that pixel over time)
    INPUT:
        data: 3d image data with time as first axis
        tmax: maximum index on time axis up to which the mean is calculated
    OUTPUT:
        normalized np.array
    KG, MS 01.2020
    '''
    if XMCD:
        return data / np.mean(data[tlim,xlim, ylim], axis=axis)
    return data - np.mean(data[tlim,xlim, ylim], axis=axis)


##################################################################################################################

#                     DISPLAY DATA

##################################################################################################################

def make_gif(data, frames, folder_save, gif_name, pixel_size, length_fraction, color = 'k', location = 1, units = 'nm',  image_suffix = '', cmap = 'viridis', duration = .5, size = 2):
    '''
    Make a GIF out of a subset of images in the sorted data array.
    INPUT:    data = data as returned by import_bbx(), sort() and normalize(); frames = list of start and stop image number; folder_save = folder where to save the images and the gif;
              gif_name = file name of the GIF; pixel_size = size of 1 pixel in nanometer for scale bar; image_suffix = string to be added to the image name; cmap = colormap, default is viridis;
              duration = time each frame is shown in the gif
    OUTPUT:   None, but every image is saved as *.png in folder_save and a GIF of all these images is saved.
    KG, 01.2020
    '''
    if not(os.path.exists(folder_save)):
        print("Creating folder " + folder_save)
        os.mkdir(folder_save)
        
    folder_tmp = folder_save + 'tmp/'
    if not(os.path.exists(folder_tmp)):
        print("Creating folder " + folder_tmp)
        os.mkdir(folder_tmp)
    
    mi = np.min(data[frames[0]:frames[1]+1])
    ma = np.max(data[frames[0]:frames[1]+1])
    
    for i in range(frames[0], frames[1]+1):
        #plot the image and save it as .png
        fig = plt.figure(frameon=False)
        fig.set_size_inches(size,size)
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        fig.add_axes(ax)
        ax.imshow(data[i], aspect='auto', cmap = cmap, vmin = mi, vmax = ma)
        scalebar = ScaleBar(pixel_size, units = units, location = location, frameon = False, color = color, fixed_value = length_fraction) 
        plt.gca().add_artist(scalebar)
        plt.savefig(folder_tmp + '%03d'%i + image_suffix + '.png', dpi=150)
        plt.close()
    #take all the images and make a GIF
    images = []
    for i in range(frames[0], frames[1]+1):
        images.append(imageio.imread(folder_tmp + '%03d'%i + image_suffix + '.png'))
    imageio.mimsave(folder_save + gif_name, images, duration = duration)
    return

def make_gif_XMCD(data, norm, frames, folder_save, gif_name, pixel_size, length_fraction, location = 1, units = 'nm',  image_suffix = '', cmap = 'coolwarm', duration = .5):
    '''
    Make a GIF out of a subset of images in the sorted data array.
    INPUT:    data = data as returned by import_bbx(), sort() and normalize(); frames = list of start and stop image number; folder_save = folder where to save the images and the gif;
              gif_name = file name of the GIF; pixel_size = size of 1 pixel in nanometer for scale bar; image_suffix = string to be added to the image name; cmap = colormap, default is viridis;
              duration = time each frame is shown in the gif
    OUTPUT:   None, but every image is saved as *.png in folder_save and a GIF of all these images is saved.
    KG, 01.2020
    '''
    if not(os.path.exists(folder_save)):
        print("Creating folder " + folder_save)
        os.mkdir(folder_save)
        
    folder_tmp = folder_save + 'tmp/'
    if not(os.path.exists(folder_tmp)):
        print("Creating folder " + folder_tmp)
        os.mkdir(folder_tmp)
        
    if norm:
        mi = np.min(data[frames[0]:frames[1]+1])
        ma = np.max(data[frames[0]:frames[1]+1])
        lim = np.max([np.abs(mi), np.abs(ma)])
        color = 'k'
    else:
        lim = np.abs(np.mean(data[:, :10, :10]))
        color = 'w'
    
    for i in range(frames[0], frames[1]+1):
        #plot the image and save it as .png
        fig = plt.figure(frameon=False)
        fig.set_size_inches(3.2,4)
        ax = plt.Axes(fig, [0., 0., 1., 1.])
        ax.set_axis_off()
        fig.add_axes(ax)
        mp = ax.imshow(data[i]/lim, aspect='auto', cmap = 'coolwarm', vmin = -1, vmax = 1)
        scalebar = ScaleBar(pixel_size, units = units, location = location, frameon = False, color = color, fixed_value = length_fraction)
        plt.gca().add_artist(scalebar)
        cb = plt.colorbar(mp, orientation="horizontal", pad = .01, shrink = .9)
        cb.set_label('Magnetization')
        plt.savefig(folder_tmp + '%03d'%i + image_suffix + '.png', dpi=150)
        plt.close()
    #take all the images and make a GIF
    images = []
    for i in range(frames[0], frames[1]+1):
        images.append(imageio.imread(folder_tmp + '%03d'%i + image_suffix + '.png'))
    imageio.mimsave(folder_save + gif_name, images, duration = duration)
    return

def plot_xmcd(data, destination, pixel_size, length_fraction, color, location = 1, units = 'nm', cmap = 'coolwarm', save = True):
    '''
    Plot XMCD image recorded at the MAXYMUS microscope at BESSY.
    INPUT:
        data: XMCD data set
        destination: filename where to save the image
        pixel_size: size of one pixel in nm (otherwise change units)
        length_fraction: length of the scale bar
        color: color of the scale bar ('w' for white and 'k' for black)
        location: location of the scale bar (default is 1, right upper corner)
        units: unit of the pixel_size (default is 'nm')
        cmap: matplotlib colormap (default is 'coolwarm')
        save: boolean variable if you want to save the image at destination (default is True)
    OUTPUT:
        no output, plots the image
    KG 01.2020
    '''
    mi = np.min(data)
    ma = np.max(data)
    lim = np.max([np.abs(mi), np.abs(ma)])
    
    #plot the image and save it as .png
    fig = plt.figure(frameon=False)
    fig.set_size_inches(3.2,4)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)
    mp = ax.imshow(data/lim, aspect='auto', cmap = 'coolwarm', vmin = -1, vmax = 1)
    scalebar = ScaleBar(pixel_size, units = units, location = location, frameon = False, color = color, fixed_value = length_fraction)
    plt.gca().add_artist(scalebar)
    cb = plt.colorbar(mp, orientation="horizontal", pad = .01, shrink = .9)
    cb.set_label('Magnetization')
    plt.savefig(destination, dpi=150)
    return

def plot(data, destination, pixel_size, length_fraction, color, location = 1, units = 'nm', cmap = 'gray', size = (2,2), save = True, scale = (0,100)):
    '''
    Plot single image recorded at the MAXYMUS microscope at BESSY.
    INPUT:
        data: data set
        destination: filename where to save the image
        pixel_size: size of one pixel in nm (otherwise change units)
        length_fraction: length of the scale bar
        color: color of the scale bar ('w' for white and 'k' for black)
        location: location of the scale bar (default is 1, right upper corner)
        units: unit of the pixel_size (default is 'nm')
        cmap: matplotlib colormap (default is 'gray')
        save: boolean variable if you want to save the image at destination (default is True)
        scale: scale of the image in percentile (default is (0,100))
    OUTPUT:
        no output, plots the image
    KG 01.2020
    '''
    mi, ma = np.percentile(data, scale)
    
    #plot the image and save it as .png
    fig = plt.figure(frameon=False)
    fig.set_size_inches(size[0], size[1])
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)
    ax.imshow(data, aspect='auto', cmap = cmap, vmin = mi, vmax = ma, origin = 'lower')
    scalebar = ScaleBar(pixel_size, units = units, frameon = False, color = color, fixed_value = length_fraction, location = location) 
    plt.gca().add_artist(scalebar)
    if save:
        plt.savefig(destination, dpi=150)
    return