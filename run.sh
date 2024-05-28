source ~/anaconda3/etc/profile.d/conda.sh
conda activate gspl

#* download dampled images
# python utils/image_downsample.py PATH_TO_DIRECTORY_THAT_STORE_IMAGES --factor 4
# python utils/image_downsample.py ./ --factor 4

#* train
CUDA_VISIBLE_DEVICES="0"  python main.py fit \
    --data.path ./data/nerf/nerf_synthetic/lego \
    --viewer \
    -n lego

# --viewer \