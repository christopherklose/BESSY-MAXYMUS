# -*- coding: utf-8 -*-
"""
For importing single .hdf5 images, and saving them as .tif images
"""

import os
import h5py
import imageio
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata


## User variables

date = '2024-04-07'
imagesNumbers = list(map(str,np.arange(10,14))) ## Put first and last+1 image number here
entryNumber = 'entry1'

interpolation = 'linear' ## 'cubic'
detector = 'APD' ## available detectors 'APD', 'timemachine', 'PMT', 'VCO'
rootPath = 'Z:\\data2'
#rootPath = 'C:\\Users\\finizio_s\\Desktop'

## Stop editing

for imageNumber in imagesNumbers:
    # Check if image exists
    imagePath = os.path.join(rootPath, date, 'Sample_Image_'+date+'_0'+imageNumber+'.hdf5')

    if not os.path.exists(imagePath):
        raise Exception("Image does not exist")
    

    # Loading and processing the data
    datasetDet = '/'+entryNumber+'/'+detector
    datasetInst = '/'+entryNumber+'/instrument'

    with h5py.File(imagePath,'r') as f:
    
        I = f[datasetDet+'/data'][()]
    
        setpx = f[datasetDet+'/sample_x'][()]
        setpy = f[datasetDet+'/sample_y'][()]
        readx = f[datasetInst+'/sample_x/data'][()]
        ready = f[datasetInst+'/sample_y/data'][()]
        data = f[datasetInst+'/'+detector+'/data'][()]
    
        X,Y = np.meshgrid(setpx, setpy)
    
        Xq = readx-np.mean(readx)
        Yq = ready-np.mean(ready)
        X = X-np.mean(X)
        Y = Y-np.mean(Y)
    
        I_pc = griddata((Xq, Yq), data, (X, Y), method=interpolation, fill_value=0)


    I = np.flip(I,0)
    I_pc = np.flip(I_pc,0)

    ## Saving the data
    
    savePath = os.path.join(rootPath, date, 'Analyzed')
    if not os.path.exists(savePath):
        os.makedirs(savePath)
    imageio.imwrite(os.path.join(savePath,'Sample_Image_'+date+'_'+imageNumber+'.tif'), I.astype(np.float32), format='tif')
    imageio.imwrite(os.path.join(savePath,'Sample_Image_'+date+'_'+imageNumber+'_posCorr.tif'), I_pc.astype(np.float32), format='tif')
