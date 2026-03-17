import glob
import os
import pickle
import shutil
from dataclasses import dataclass
from typing import Dict, Tuple

import h5py
import numpy as np
import tyro
from natsort import natsorted
from tqdm import tqdm

from gello.data_utils.plot_utils import plot_in_grid

np.set_printoptions(precision=3, suppress=True)

import mediapy as mp

from gello.data_utils.conversion_utils import preproc_obs


def _stack_dict_list(dict_list):
    """Stack a list of nested dicts into a single dict with numpy arrays.
    Replacement for DictArray.stack from gdict."""
    if not dict_list:
        return {}
    keys = dict_list[0].keys()
    result = {}
    for key in keys:
        values = [d[key] for d in dict_list]
        if isinstance(values[0], dict):
            result[key] = _stack_dict_list(values)
        elif isinstance(values[0], np.ndarray):
            result[key] = np.stack(values, axis=0)
        else:
            result[key] = np.array(values)
    return result


def _save_dict_to_hdf5(data: Dict, filepath: str):
    """Save a nested dict of numpy arrays to HDF5.
    Replacement for GDict.to_hdf5 from gdict."""
    with h5py.File(filepath, "w") as f:
        _write_dict_to_hdf5_group(f, data)


def _write_dict_to_hdf5_group(group, data):
    for key, value in data.items():
        if isinstance(value, dict):
            subgroup = group.create_group(key)
            _write_dict_to_hdf5_group(subgroup, value)
        elif isinstance(value, np.ndarray):
            group.create_dataset(key, data=value)
        else:
            group.create_dataset(key, data=np.array(value))


def _make_grid_video_from_numpy(videos, ncols, output_path, fps=30):
    """Create a grid video from a list of numpy video arrays.
    Replacement for make_grid_video_from_numpy from simple_bc."""
    if not videos:
        return
    # Pad videos to the same length
    max_len = max(v.shape[0] for v in videos)
    padded = []
    for v in videos:
        if v.shape[0] < max_len:
            pad = np.zeros((max_len - v.shape[0], *v.shape[1:]), dtype=v.dtype)
            v = np.concatenate([v, pad], axis=0)
        padded.append(v)

    nrows = (len(padded) + ncols - 1) // ncols
    # Pad list to fill grid
    while len(padded) < nrows * ncols:
        padded.append(np.zeros_like(padded[0]))

    rows = []
    for r in range(nrows):
        row = np.concatenate(padded[r * ncols : (r + 1) * ncols], axis=2)
        rows.append(row)
    grid = np.concatenate(rows, axis=1)

    mp.write_video(output_path, grid, fps=fps)


# def get_act_bounds(source_dir: str) -> np.ndarray:
#     pkls = natsorted(
#         glob.glob(os.path.join(source_dir, "**/*.pkl"), recursive=True), reverse=True
#     )
#     if len(pkls) <= 30:
#         print(f"Skipping {source_dir} because it has less than 30 frames.")
#         return None
#     pkls = pkls[:-5]
#
#     scale_factor = None
#     for pkl in pkls:
#         try:
#             with open(pkl, "rb") as f:
#                 demo = pickle.load(f)
#         except Exception as e:
#             print(f"Skipping {pkl} because it is corrupted.")
#             print(f"Error: {e}")
#             raise Exception("Corrupted pkl")
#
#         requested_control = demo.pop("control")
#         curr_scale_factor = np.abs(requested_control)
#         if scale_factor is None:
#             scale_factor = curr_scale_factor
#         else:
#             scale_factor = np.maximum(scale_factor, curr_scale_factor)
#     assert scale_factor is not None
#     return scale_factor


def get_act_min_max(source_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    pkls = natsorted(
        glob.glob(os.path.join(source_dir, "**/*.pkl"), recursive=True), reverse=True
    )
    if len(pkls) <= 30:
        print(f"Skipping {source_dir} because it has less than 30 frames.")
        raise RuntimeError("Too few frames")
    pkls = pkls[:-5]

    scale_min = None
    scale_max = None
    for pkl in pkls:
        try:
            with open(pkl, "rb") as f:
                demo = pickle.load(f)
        except Exception as e:
            print(f"Skipping {pkl} because it is corrupted.")
            print(f"Error: {e}")
            raise Exception("Corrupted pkl")

        requested_control = demo.pop("control")
        curr_scale_factor = requested_control
        if scale_min is None:
            assert scale_max is None
            scale_min = curr_scale_factor
            scale_max = curr_scale_factor
        else:
            assert scale_max is not None
            scale_min = np.minimum(scale_min, curr_scale_factor)
            scale_max = np.maximum(scale_min, curr_scale_factor)

    assert scale_min is not None
    assert scale_max is not None
    return scale_min, scale_max


def convert_single_demo(
    source_dir,
    i,
    traj_output_dir,
    rgb_output_dir,
    depth_output_dir,
    state_output_dir,
    action_output_dir,
    scale_factor,
    bias_factor,
):
    """
    1. converts the demo into a gdict
    2. visualizes the RGB of the demo
    3. visualizes the state + action space of the demo
    4. returns these to be collated by the caller.
    """

    pkls = natsorted(
        glob.glob(os.path.join(source_dir, "**/*.pkl"), recursive=True), reverse=True
    )
    demo_stack = []

    if len(pkls) <= 30:
        return 0

    # go through the demo in reverse order.
    # remove the first few frames because they are not useful.
    pkls = pkls[:-5]

    for pkl in pkls:
        curr_ts = {}
        try:
            with open(pkl, "rb") as f:
                demo = pickle.load(f)
        except:
            print(f"Skipping {pkl} because it is corrupted.")
            return 0

        obs = preproc_obs(demo)
        action = demo.pop("control")
        action = (action - bias_factor) / scale_factor  # normalize between -1 and 1

        curr_ts["obs"] = obs
        curr_ts["actions"] = action
        curr_ts["dones"] = np.zeros(1)  # random fill
        curr_ts["episode_dones"] = np.zeros(1)  # random fill

        curr_ts_wrapped = dict()
        curr_ts_wrapped[f"traj_{i}"] = curr_ts
        demo_stack = [curr_ts_wrapped] + demo_stack

    # Stack all timesteps: each item is {"traj_i": {"obs": ..., "actions": ...}}
    inner_dicts = [d[f"traj_{i}"] for d in demo_stack]
    stacked = _stack_dict_list(inner_dicts)
    demo_dict = {f"traj_{i}": stacked}
    _save_dict_to_hdf5(demo_dict, os.path.join(traj_output_dir, f"traj_{i}.h5"))

    ## save the base videos
    # save the base rgb and depth videos
    all_rgbs = demo_dict[f"traj_{i}"]["obs"]["rgb"][:, 1].transpose([0, 2, 3, 1])
    all_rgbs = all_rgbs.astype(np.uint8)
    _, H, W, _ = all_rgbs.shape
    all_depths = demo_dict[f"traj_{i}"]["obs"]["depth"][:, 1].reshape([-1, H, W])
    all_depths = all_depths / 5.0  # scale to 0-1

    mp.write_video(
        os.path.join(rgb_output_dir + "", f"traj_{i}_rgb_base.mp4"), all_rgbs, fps=30
    )
    mp.write_video(
        os.path.join(depth_output_dir + "", f"traj_{i}_depth_base.mp4"),
        all_depths,
        fps=30,
    )

    ## save the wrist videos
    # save the rgb and depth videos
    all_rgbs = demo_dict[f"traj_{i}"]["obs"]["rgb"][:, 0].transpose([0, 2, 3, 1])
    all_rgbs = all_rgbs.astype(np.uint8)
    _, H, W, _ = all_rgbs.shape
    all_depths = demo_dict[f"traj_{i}"]["obs"]["depth"][:, 0].reshape([-1, H, W])
    all_depths = all_depths / 2.0  # scale to 0-1

    mp.write_video(
        os.path.join(rgb_output_dir + "", f"traj_{i}_rgb_wrist.mp4"), all_rgbs, fps=30
    )
    mp.write_video(
        os.path.join(depth_output_dir + "", f"traj_{i}_depth_wrist.mp4"),
        all_depths,
        fps=30,
    )
    ##

    all_depths = np.tile(all_depths[..., None], [1, 1, 1, 3])

    # save the state and action plots
    all_actions = demo_dict[f"traj_{i}"]["actions"]
    all_states = demo_dict[f"traj_{i}"]["obs"]["state"]

    curr_actions = all_actions.reshape([1, *all_actions.shape])
    curr_states = all_states.reshape([-1, *all_states.shape])

    plot_in_grid(
        curr_actions, os.path.join(action_output_dir + "", f"traj_{i}_actions.png")
    )
    plot_in_grid(
        curr_states, os.path.join(state_output_dir + "", f"traj_{i}_states.png")
    )

    return all_rgbs, all_depths, all_actions, all_states


@dataclass
class Args:
    source_dir: str
    vis: bool = True


def main(args):
    subdirs = natsorted(glob.glob(os.path.join(args.source_dir, "*/"), recursive=True))

    if not subdirs:
        print(f"ERROR: No subdirectories found in '{args.source_dir}'")
        print("Expected directory structure: <source-dir>/<subdir_1>/<demo_files.pkl>")
        print("                               <source-dir>/<subdir_2>/<demo_files.pkl>")
        print("                               ...")
        exit(1)

    output_dir = args.source_dir
    if output_dir[-1] == "/":
        output_dir = output_dir[:-1]

    output_dir = os.path.join(output_dir, "_conv")

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    output_dir = os.path.join(output_dir, "multiview")

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    else:
        print(f"Output directory {output_dir} already exists, and will be deleted")
        shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    train_dir = os.path.join(output_dir, "train")
    val_dir = os.path.join(output_dir, "val")

    if not os.path.isdir(train_dir):
        os.makedirs(train_dir, exist_ok=True)
    if not os.path.isdir(val_dir):
        os.makedirs(val_dir, exist_ok=True)

    val_size = int(min(0.1 * len(subdirs), 10))
    val_indices = np.random.choice(len(subdirs), size=val_size, replace=False)
    val_indices = set(val_indices)

    print("Computing scale factors")
    pbar = tqdm(range(len(subdirs)))
    min_scale_factor = None
    max_scale_factor = None
    for i in pbar:
        try:
            curr_min, curr_max = get_act_min_max(subdirs[i])
            if min_scale_factor is None:
                assert max_scale_factor is None
                min_scale_factor = curr_min
                max_scale_factor = curr_max
            else:
                assert max_scale_factor is not None
                min_scale_factor = np.minimum(min_scale_factor, curr_min)
                max_scale_factor = np.maximum(max_scale_factor, curr_max)
            pbar.set_description(f"t: {i}")
        except Exception as e:
            print(f"Error: {e}")
            print(f"Skipping {subdirs[i]}")
            continue

    if min_scale_factor is None or max_scale_factor is None:
        print("ERROR: No valid data subdirectories found in", args.source_dir)
        print("Expected subdirectories with *.pkl files. Current structure:")
        print(f"  data/")
        for d in subdirs:
            print(f"    {d}")
        print(
            "\nPlease ensure your data is in the format: data/<subdirectory>/<frames>.pkl"
        )
        exit(1)

    bias_factor = (min_scale_factor + max_scale_factor) / 2.0
    scale_factor = (max_scale_factor - min_scale_factor) / 2.0
    scale_factor[scale_factor == 0] = 1.0
    print("*" * 80)
    print(f"scale factors: {scale_factor}")
    print(f"bias factor: {bias_factor}")
    # make it into a copy pasteable string where the numbers are separated by commas
    scale_factor_str = ", ".join([f"{x}" for x in scale_factor])
    print(f"scale_factor = np.array([{scale_factor_str}])")
    bias_factor_str = ", ".join([f"{x}" for x in bias_factor])
    print(f"bias_factor = np.array([{bias_factor_str}])")
    print("*" * 80)

    tot = 0

    all_rgbs = []
    all_depths = []
    all_actions = []
    all_states = []

    vis_dir = os.path.join(output_dir, "vis")
    state_output_dir = os.path.join(vis_dir, "state")
    action_output_dir = os.path.join(vis_dir, "action")
    rgb_output_dir = os.path.join(vis_dir, "rgb")
    depth_output_dir = os.path.join(vis_dir, "depth")

    if not os.path.isdir(vis_dir):
        os.makedirs(vis_dir, exist_ok=True)
    if not os.path.isdir(state_output_dir):
        os.makedirs(state_output_dir, exist_ok=True)
    if not os.path.isdir(action_output_dir):
        os.makedirs(action_output_dir, exist_ok=True)
    if not os.path.isdir(rgb_output_dir):
        os.makedirs(rgb_output_dir, exist_ok=True)
    if not os.path.isdir(depth_output_dir):
        os.makedirs(depth_output_dir, exist_ok=True)

    pbar = tqdm(range(len(subdirs)))
    for i in pbar:
        out_dir = val_dir if i in val_indices else train_dir
        out_dir = os.path.join(out_dir, "none")

        if not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        ret = convert_single_demo(
            subdirs[i],
            i,
            out_dir,
            rgb_output_dir,
            depth_output_dir,
            state_output_dir,
            action_output_dir,
            scale_factor=scale_factor,
            bias_factor=bias_factor,
        )

        if ret != 0:
            all_rgbs.append(ret[0])
            all_depths.append(ret[1])
            all_actions.append(ret[2])
            all_states.append(ret[3])
            tot += 1

        pbar.set_description(f"t: {i}")

    print(
        f"Finished converting all demos to {output_dir}! (num demos: {tot} / {len(subdirs)})"
    )

    if args.vis:
        if len(all_rgbs) > 0:
            print(f"Visualizing all demos...")

            plot_in_grid(
                all_actions, os.path.join(action_output_dir, "_all_actions.png")
            )
            plot_in_grid(all_states, os.path.join(state_output_dir, "_all_states.png"))
            _make_grid_video_from_numpy(
                all_rgbs, 10, os.path.join(rgb_output_dir, "_all_rgb.mp4"), fps=30
            )
            _make_grid_video_from_numpy(
                all_depths, 10, os.path.join(depth_output_dir, "_all_depth.mp4"), fps=30
            )

    exit(0)


if __name__ == "__main__":
    main(tyro.cli(Args))
