#!/usr/bin/env python3

import json
import pathlib
import subprocess

import click


# These tags are information about a file, rather than information _in_ the file
# We care only about file contents when comparing files.
IGNORE_TAGS = {
    'Directory',
    'FileAccessDate',
    'FileInodeChangeDate',
    'FileModifyDate',
    'FileName',
    'FilePermissions',
    'FileType',
    'FileTypeExtension',
    'SourceFile',
}


def exiftool_extract_icc(filename):
    """Extract all tags from ICC profile and load into dictionary.

    Binary tags are dumped as hex.
    I'm writing this on top of exiftool because the iccdump tool in argyll-cms
    throws errors like:

    > Unable to read: 1, icmCurve_read: Wrong tag type for icmCurve
    """
    command = ['exiftool', '-e', '-j', '-s', str(filename)]
    result = subprocess.run(command, capture_output=True, check=True)

    icc = json.loads(result.stdout)[0]

    # remove ignored tags
    # - exiftool still prints e.g. SourceFile even if it's excluded with --SourceFile
    icc = {k: v for k, v in icc.items() if k not in IGNORE_TAGS}

    # Grab binary data from ICC
    for k, v in icc.items():
        if isinstance(v, str) and 'use -b option to extract' in v:
            # replace value with binary data
            command = ['exiftool', '-b', f'-{k}', str(filename)]
            print(f'   Extracting binary data from tag {k} ...')
            tag_result = subprocess.run(command, capture_output=True, check=True)
            icc[k] = ' '.join(['%02x' % c for c in tag_result.stdout])

    return icc


@click.command()
@click.argument('profile_dir')
@click.argument('output_dir')
def click_main(profile_dir, output_dir):
    profile_dir = pathlib.Path(profile_dir)
    output_dir = pathlib.Path(output_dir)

    for input_icc_path in profile_dir.glob('*.icc'):
        dumped_path = output_dir / (input_icc_path.stem + '.json')
        print(f'Dumping {input_icc_path} to {dumped_path} ...')

        icc = exiftool_extract_icc(input_icc_path)

        with open(dumped_path, 'w') as out:
            json.dump(icc, out, sort_keys=True, indent=4)

    print('DONE.')


if __name__ == '__main__':
    click_main()
