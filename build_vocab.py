import tempfile
import os
import argparse

import sentencepiece
import tensorflow as tf

from tokenization import JapaneseBasicTokenizer


SPECIAL_SYMBOLS = ["<unk>", "<s>", "</s>"]
CONTROL_SYMBOLS = ["[PAD]", "[CLS]", "[SEP]", "[MASK]"]


def main(args):
    tokenizer = JapaneseBasicTokenizer(args.do_lower_case, args.mecab_dict)
    with tempfile.TemporaryDirectory() as tempdir:
        # read input files and write to a temporary file
        concat_input_file = open(os.path.join(tempdir, "input.txt"), "w")
        for input_file in tf.gfile.Glob(args.input_file):
            with tf.gfile.GFile(input_file, "r") as reader:
                tf.logging.info(f"Reading {input_file}")
                for line in reader:
                    tokens = tokenizer.tokenize(line.strip('\n'))
                    print(" ".join(tokens), file=concat_input_file)

        # train a SentencePiece model and store the vocabulary file to a temp directory
        tf.logging.info("Training a SentencePiece model")
        commands = {
            "input": concat_input_file.name,
            "model_type": "bpm",
            "model_prefix": os.path.join(tempdir, "sentencepiece"),
            "vocab_size": args.vocab_size,
            "control_symbols": ",".join(CONTROL_SYMBOLS),
            "input_sentence_size": args.sentence_size,
            "shuffle_input_sentence": "true"
        }
        command_line = " ".join([f"--{key}={value}" for key, value in commands.items()])
        sentencepiece.SentencePieceTrainer.Train(command_line)
        concat_input_file.close()

        # convert SentencePiece vocabulary into WordPiece format that is used in BERT
        with open(os.path.join(tempdir, "sentencepiece.vocab")) as vocab_file, \
             tf.gfile.GFile(args.output_file, "wt") as output_file:
            for line in vocab_file:
                sp_token, _ = line.rstrip("\n").split("\t")
                if sp_token in SPECIAL_SYMBOLS + CONTROL_SYMBOLS:
                    # e.g. "[MASK]" -> "[MASK]"
                    wp_token = sp_token
                elif sp_token.startswith("\u2581"):
                    # e.g. "▁word" -> "word"
                    wp_token = sp_token[1:]
                else:
                    # e.g. "tion" -> "##tion"
                    wp_token = "##" + sp_token

                output_file.write(f"{wp_token}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str,
        help="Input raw text file (or comma-separated list of files).")
    parser.add_argument("output_file", type=str,
        help="Output vocabulary file.")
    parser.add_argument("--vocab_size", type=int, default=32000,
        help="WordPiece vocabulary size. [32000]")
    parser.add_argument("--sentence_size", type=int, default=1000000,
        help="Limit the input sentence size. [1000000]")
    parser.add_argument("--do_lower_case", type=bool, default=False,
        help="Whether to lower case the input text. [False]")
    parser.add_argument("--mecab_dict", type=str,
        help="Path to MeCab custom dictionary.")
    args = parser.parse_args()

    main(args)
