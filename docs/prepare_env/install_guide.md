# Prepare the Environment
[中文文档](./install_guide-zh.md)

This guide is about building a python environment for Real3D-Portrait with Conda.

The following installation process is verified in A100/V100 + CUDA11.7.

# 0. Install Conda
https://docs.anaconda.com/free/anaconda/install/linux/


 Add conda to path (for ease of use)
 open .bashrc file on ~/.bashrc with nano and add this line to end of file with ctrl-o and enter and ctrl+x to exit

 export PATH=~/anaconda3/bin:$PATH

# 1. Install CUDA
 We recommend to install CUDA `11.7` (which is verified in various types of GPUs), but other CUDA versions (such as `10.2`, `12.x`) may also work well. https://developer.nvidia.com/cuda-11-7-0-download-archive

 Add cuda libs to path (or get faceslap errors)
 open .bashrc file on ~/.bashrc with nano and add this line to end of file save with ctrl-o and enter and ctrl+x to exit
 
 export LD_LIBRARY_PATH=/usr/lib/wsl/lib:$LD_LIBRARY_PATH

# 2. Install Python Packages
```
cd <Real3DPortraitRoot>
source <CondaRoot>/bin/activate
conda create -n real3dportrait python=3.9
conda activate real3dportrait
conda install conda-forge::ffmpeg # ffmpeg with libx264 codec to turn images to video

### We recommend torch2.0.1+cuda11.7. 
conda install pytorch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 pytorch-cuda=11.7 -c pytorch -c nvidia

# Install from pytorch3d from conda (For fast installation, Linux only)
conda install pytorch3d::pytorch3d
## Alternatively, a choice of compatibility, build from Github's source code. 
## It may take a long time (maybe tens of minutes), Proxy is recommended if encountering the time-out problem
pip install "git+https://github.com/facebookresearch/pytorch3d.git@stable"

# MMCV for some network structure
pip install cython
pip install openmim==0.3.9
mim install mmcv==2.1.0 # use mim to speed up installation for mmcv

# other dependencies
pip install -r docs/prepare_env/requirements.txt -v

If you encounter the following error, please try to install the dependencies with the following command:
pip install -r docs/prepare_env/requirements.txt -v --use-deprecated=legacy-resolver

> ERROR: pip's dependency resolver does not currently take into account all the packages
> that are installed. This behaviour is the source of the following dependency conflicts.
> openxlab 0.0.34 requires setuptools~=60.2.0, but you have setuptools 69.1.1 which is incompatible.

```
