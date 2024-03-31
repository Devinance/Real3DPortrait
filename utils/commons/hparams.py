import argparse
import json
import os
import yaml

from utils.commons.os_utils import remove_file

global_print_hparams = True
hparams = {}


class Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)


def override_config(old_config: dict, new_config: dict):
    if new_config.get('__replace', False):
        old_config.clear()
    for k, v in new_config.items():
        if isinstance(v, dict) and k in old_config:
            override_config(old_config[k], new_config[k])
        else:
            old_config[k] = v


def traverse_dict(d, func):
    for k in d.keys():
        v = d[k]
        if isinstance(v, dict):
            traverse_dict(v, func)
        else:
            d[k] = func(v)


def parse_config_ref(v):
    if isinstance(v, str) and v.startswith('^'):
        return load_config(v[1:], [], set())
    return v


def remove_meta_key(d):
    for k in list(d.keys()):
        v = d[k]
        if isinstance(v, dict):
            remove_meta_key(v)
        else:
            if k[:2] == '__':
                del d[k]


def load_config(config_fn, config_chains, loaded_configs):
    # deep first inheritance and avoid the second visit of one node
    if not os.path.exists(config_fn):
        print(f"| WARN: {config_fn} not exist.", )
        return {}
    with open(config_fn) as f:
        hparams_ = yaml.safe_load(f)
    loaded_configs.add(config_fn)

    traverse_dict(hparams_, parse_config_ref)

    if 'base_config' in hparams_:
        ret_hparams = {}
        if not isinstance(hparams_['base_config'], list):
            hparams_['base_config'] = [hparams_['base_config']]
        for c in hparams_['base_config']:
            if c.startswith('.'):
                c = f'{os.path.dirname(config_fn)}/{c}'
                c = os.path.normpath(c)
            if c not in loaded_configs:
                override_config(ret_hparams, load_config(c, config_chains, loaded_configs))
        override_config(ret_hparams, hparams_)
    else:
        ret_hparams = hparams_

    config_chains.append(config_fn)
    return ret_hparams


def set_hparams(config='', exp_name='', hparams_str='', print_hparams=True, global_hparams=True):
    if config == '' and exp_name == '':
        parser = argparse.ArgumentParser(description='')
        parser.add_argument('--config', type=str, default='',
                            help='location of the data corpus')
        parser.add_argument('--exp_name', type=str, default='', help='exp_name')
        parser.add_argument('-hp', '--hparams', type=str, default='',
                            help='location of the data corpus')
        parser.add_argument('--infer', action='store_true', help='infer')
        parser.add_argument('--validate', action='store_true', help='validate')
        parser.add_argument('--reset', action='store_true', help='reset hparams')
        parser.add_argument('--remove', action='store_true', help='remove old ckpt')
        parser.add_argument('--debug', action='store_true', help='debug')
        parser.add_argument('--start_rank', type=int, default=0, help='the start rank id for DDP, keep 0 when single-machine multi-GPU')
        parser.add_argument('--world_size', type=int, default=-1, help='the total number of GPU used across all machines, keep -1 for single-machine multi-GPU')
        parser.add_argument('--init_method', type=str, default='tcp', help='method to init ddp, use tcp or file')

        args, unknown = parser.parse_known_args()
        if print_hparams:
            print("| set_hparams Unknow hparams: ", unknown)
    else:
        args = Args(config=config, exp_name=exp_name, hparams=hparams_str,
                    infer=False, validate=False, reset=False, debug=False, remove=False, start_rank=0, world_size=-1, init_method='tcp')
    global hparams
    assert args.config != '' or args.exp_name != ''
    if args.config != '':
        assert os.path.exists(args.config), args.config

    saved_hparams = {}
    args_work_dir = ''
    if args.exp_name != '':
        args_work_dir = f'checkpoints/{args.exp_name}'
        ckpt_config_path = f'{args_work_dir}/config.yaml'
        if os.path.exists(ckpt_config_path):
            with open(ckpt_config_path) as f:
                saved_hparams_ = yaml.safe_load(f)
                if saved_hparams_ is not None:
                    saved_hparams.update(saved_hparams_)
    hparams_ = {}
    config_chains = []
    if args.config != '':
        hparams_.update(load_config(args.config, config_chains, set()))
        if len(config_chains) > 1 and print_hparams:
            print('| Hparams chains: ', config_chains)
    if not args.reset:
        hparams_.update(saved_hparams)
    hparams_['work_dir'] = args_work_dir

    # Support config overriding in command line. Support list type config overriding.
    # Examples: --hparams="a=1,b.c=2,d=[1 1 1]"
    if args.hparams != "":
        for new_hparam in args.hparams.split(","):
            k, v = new_hparam.split("=")
            v = v.strip("\'\" ")
            config_node = hparams_
            for k_ in k.split(".")[:-1]:
                config_node = config_node[k_]
            k = k.split(".")[-1]
            if k in config_node:
                if v in ['True', 'False'] or type(config_node[k]) in [bool, list, dict]:
                    if type(config_node[k]) == list:
                        v = v.replace(" ", ",").replace('^', "\"")
                        if '|' in v:
                            tp = type(config_node[k][0]) if len(config_node[k]) else str
                            config_node[k] = [tp(x) for x in v.split("|") if x != '']
                            continue
                    config_node[k] = eval(v)
                else:
                    config_node[k] = type(config_node[k])(v)
            else:
                config_node[k] = v
                try:
                    config_node[k] = float(v)
                except:
                    pass
                try:
                    config_node[k] = int(v)
                except:
                    pass
                if v.lower() in ['false', 'true']:
                    config_node[k] = v.lower() == 'true'
    if args_work_dir != '' and args.remove:
        answer = input("REMOVE old checkpoint? Y/N [Default: N]: ")
        if answer.lower() == "y":
            remove_file(args_work_dir)
    if args_work_dir != '' and (not os.path.exists(ckpt_config_path) or args.reset) and not args.infer:
        os.makedirs(hparams_['work_dir'], exist_ok=True)
        with open(ckpt_config_path, 'w') as f:
            yaml.safe_dump(hparams_, f)

    hparams_['infer'] = args.infer
    hparams_['debug'] = args.debug
    hparams_['validate'] = args.validate
    hparams_['exp_name'] = args.exp_name

    hparams_['start_rank'] = args.start_rank # useful for multi-machine training
    hparams_['world_size'] = args.world_size
    hparams_['init_method'] = args.init_method

    remove_meta_key(hparams_)
    global global_print_hparams
    if global_hparams:
        hparams.clear()
        hparams.update(hparams_)
    if print_hparams and global_print_hparams and global_hparams:
        print('| Hparams: ', json.dumps(hparams_, indent=2, sort_keys=True))
        # for i, (k, v) in enumerate(sorted(hparams_.items())):
        #     print(f"\033[;33;m{k}\033[0m: {v}, ", end="\n" if i % 5 == 4 else "")
        global_print_hparams = False
    return hparams_

if __name__ == '__main__':
    set_hparams('checkpoints/1205_os_secc2planes/os_secc2plane_trigridv2/config.yaml')