#!/usr/bin/env python3

import csv
import hashlib
import logging
import os
import pathlib
from string import (
    Template,
)
from subprocess import (
    PIPE,
    Popen,
)
import sys
from tempfile import (
    TemporaryDirectory,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def run_with_checks(command, args, input=None):
    """
    Runs the given executable with error reporting.
    """
    p = Popen(
        (command,) + args,
        stdin=None if input is None else PIPE,
        stdout=PIPE, stderr=PIPE,
    )

    if p.returncode is not None:
        raise RuntimeError('{} exited with status {} before communication: {}'.format(
            command,
            p.returncode,
            p.stderr.read(),
        ))

    try:
        out, err = p.communicate(input=input)
    except OSError:
        raise RuntimeError('{} exited with status {} during communication'.format(
            command,
            p.returncode,
        ))

    if p.returncode != 0:
        raise RuntimeError('{} exited with status {} during communication. stdout: {}, stderr: {}'.format(
            command,
            p.returncode,
            out.decode('utf-8'),
            err.decode('utf-8'),
        ))

    return out.decode('utf-8')


def tex_to_png(tex_content, res=24 * 96):
    encoded_content = tex_content.encode('utf-8')
    hsh = hashlib.md5(encoded_content).hexdigest()

    with TemporaryDirectory() as tmp_dir:
        run_with_checks(
            'xelatex',
            ('-output-directory', tmp_dir, '-jobname', hsh, '--'),
            input=encoded_content,
        )

        pdf_file = os.path.join(tmp_dir, hsh + '.pdf')
        pdf_cropped_file = os.path.join(tmp_dir, hsh + '-cropped.pdf')
        png_file = os.path.join(tmp_dir, hsh + '.png')

        run_with_checks('pdfcrop', (pdf_file, pdf_cropped_file))
        run_with_checks('gs', (
            '-o', png_file,
            f'-r{res}',
            '-sDEVICE=pngalpha',
            '-dAlignToPixels=1',
            '-dGridFitTT=2',
            '-dTextAlphaBits=4',
            '-dGraphicsAlphaBits=4',
            pdf_cropped_file,
        ))

        with open(png_file, 'rb') as f:
            return f.read()


def main():
    with open('template.tex', 'r') as f:
        template = Template(f.read())

    prefix = sys.argv[1]
    reader = csv.reader(sys.stdin)

    with open('cards.txt', 'w') as cards_file:
        for content, name in reader:
            tex_content = template.substitute(content=content)
            png_content = tex_to_png(tex_content)

            output_dir = pathlib.Path('output')
            png_file = f'{prefix}-{name}.png'
            png_file_path = output_dir / png_file

            logger.info(f'Writing to {png_file_path}...')

            with open(png_file_path, 'wb') as f:
                f.write(png_content)

            cards_file.write(f'<img src="{png_file}">; {name}\n')


if __name__ == '__main__':
    main()
