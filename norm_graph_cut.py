"""Normalized graph cuts for segmentator (experimental)."""

import ncut_prepare
import os
import numpy as np
from matplotlib import animation
from matplotlib import pyplot as plt
from skimage.filters import gaussian
from skimage.future import graph
from skimage.morphology import square, closing
from skimage.segmentation import slic


def norm_grap_cut(image, closing_size=5, max_edge=10000000, max_rec=3,
                  compactness=5, nrSupPix=2000, ):
    """
    Normalized graph cut wrapper for 2D numpy arrays.

    Arguments:
    -----------
        image: np.ndarray (2D)
            Volume histogram.
        closing_size: int, positive
            determines dilation size closing operation.
        max_edge: float, optional
            The maximum possible value of an edge in the RAG. This corresponds
            to an edge between identical regions. This is used to put self
            edges in the RAG.
        compactness: float
            From skimage slic_superpixels.py slic function:
            Balances color proximity and space proximity. Higher values give
            more weight to space proximity, making superpixel shapes more
            square/cubic. This parameter depends strongly on image contrast and
            on the shapes of objects in the image.
        nrSupPix: int, positive
            The (approximate) number of superpixels in the region adjacency
            graph.

    Returns:
    -----------
        sector_mask: np.ndarray (2D)
            Segmented volume histogram mask image. Each label has a unique
            identifier.
    """
    # truncate very high values to gain precision later in uint8 conversion
    perc = np.percentile(image, 99.75)
    image[image > perc] = perc

    # scale for uint8 conversion
    image = np.round(255 / image.max() * image)
    image = image.astype('uint8')

    # # dilate and erode (closing) to fill in white dots in grays (arbitrary)
    # image = closing(image, square(closing_size))

    # scikit implementation expects rgb format (shape: NxMx3)
    image = np.tile(image, (3, 1, 1))
    image = np.transpose(image, (1, 2, 0))

    labels1 = slic(image, compactness=compactness, n_segments=nrSupPix,
                   sigma=2)
    # region adjacency graph (rag)
    g = graph.rag_mean_color(img, labels1, mode='similarity_and_proximity')
    labels2 = graph.cut_normalized(labels1, g, max_edge=max_edge,
                                   num_cuts=1000, max_rec=max_rec)
    return labels2, labels1


path = ncut_prepare.args.filename
basename = path.split(os.extsep, 1)[0]

img = np.load(path)
img = np.log10(img+1)

max_recursion = ncut_prepare.args.maxRec
ncut = np.zeros((img.shape[0], img.shape[1], max_recursion + 1))
for i in range(0, max_recursion + 1):
    msk, regions = norm_grap_cut(img, max_rec=i,
                                 nrSupPix=ncut_prepare.args.nrSupPix,
                                 compactness=ncut_prepare.args.compactness)
    ncut[:, :, i] = msk

# plots
fig = plt.figure()
ax1 = fig.add_subplot(121)
ax2 = fig.add_subplot(122)

# ax1.imshow(img.T, origin="lower", cmap=plt.cm.inferno)
ax1.imshow(regions.T, origin="lower", cmap=plt.cm.inferno)
ax2.imshow(msk.T, origin="lower", cmap=plt.cm.nipy_spectral)

ax1.set_title('Source')
ax2.set_title('Ncut')

plt.show()

fig = plt.figure()
unq = np.unique(msk)
idx = -1

im = plt.imshow(msk.T, origin="lower", cmap=plt.cm.flag,
                animated=True)


def updatefig(*args):
    """Animate the plot."""
    global unq, msk, idx, tmp
    idx += 1
    idx = idx % ncut.shape[2]
    tmp = np.copy(ncut[:, :, idx])
    im.set_array(tmp.T)
    return im,


ani = animation.FuncAnimation(fig, updatefig, interval=750, blit=True)
plt.show()

outName = basename + '_ncut' + '_sp' + str(ncut_prepare.args.nrSupPix) \
          + '_c' + str(ncut_prepare.args.compactness)
outName = outName.replace('.', 'pt')
np.save(outName, ncut)
