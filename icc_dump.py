#!/usr/bin/env python3

import json
import pathlib
import subprocess

import click


# These tags are information about a file, rather than information _in_ the file.
# We care only about file contents when comparing files.
IGNORE_TAGS = {
    'Directory',
    'ExifToolVersion',
    'FileAccessDate',
    'FileInodeChangeDate',
    'FileModifyDate',
    'FileName',
    'FilePermissions',
    'FileSize',
    'FileType',
    'FileTypeExtension',
    'MIMEType',
    'SourceFile',
}


def exiftool_extract_icc(filename, hex_ids):
    """Extract all tags from ICC profile and load into dictionary.

    Binary tags are dumped as hex.
    I'm writing this on top of exiftool because the iccdump tool in argyll-cms
    throws errors like:

    > Unable to read: 1, icmCurve_read: Wrong tag type for icmCurve
    """
    # Together, the -u and -U arguments dump unknown tags
    base_command = ['exiftool', '-e', '-u', '-U']
    hex_id_arg = ['-hex'] if hex_ids else []
    command = base_command + ['-j'] + hex_id_arg + [str(filename)]
    result = subprocess.run(command, capture_output=True, check=True)
    icc = json.loads(result.stdout)[0]

    # remove ignored tags
    # - exiftool still prints e.g. SourceFile even if it's excluded with --SourceFile
    icc = {k: v for k, v in icc.items() if k not in IGNORE_TAGS}

    # Grab binary data from ICC
    for k, v in icc.items():
        if hex_ids:
            v = v['val']
        if isinstance(v, str) and 'use -b option to extract' in v:
            # replace value with binary data
            command = base_command + ['-b', f'-{k}', str(filename)]
            print(f'   Extracting binary data from tag {k} ...')
            tag_result = subprocess.run(command, capture_output=True, check=True)
            hexdump = ' '.join(['%02x' % c for c in tag_result.stdout])
            if hex_ids:
                icc[k]['val'] = hexdump
            else:
                icc[k] = hexdump

    return icc


@click.command()
@click.option('--hex-ids', is_flag=True, help='Include tag hex IDs in output')
@click.argument('profile_dir')
@click.argument('output_dir')
def click_main(profile_dir, output_dir, hex_ids):
    profile_dir = pathlib.Path(profile_dir)
    output_dir = pathlib.Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    for input_icc_path in profile_dir.glob('*.icc'):
        dumped_path = output_dir / (input_icc_path.stem + '.json')
        print(f'Dumping {input_icc_path} to {dumped_path} ...')

        icc = exiftool_extract_icc(input_icc_path, hex_ids)

        with open(dumped_path, 'w') as out:
            json.dump(icc, out, sort_keys=True, indent=4)

    print('DONE.')


if __name__ == '__main__':
    click_main()
