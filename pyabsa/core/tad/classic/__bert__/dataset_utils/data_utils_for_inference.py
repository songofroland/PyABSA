# -*- coding: utf-8 -*-
# file: data_utils.py
# author: songyouwei <youwei0314@gmail.com>
# Copyright (C) 2018. All Rights Reserved.

import numpy as np
import tqdm
from torch.utils.data import Dataset
from transformers import AutoTokenizer

from pyabsa.core.apc.dataset_utils.apc_utils import load_apc_datasets, LABEL_PADDING


class Tokenizer4Pretraining:
    def __init__(self, max_seq_len, opt):
        self.tokenizer = AutoTokenizer.from_pretrained(opt.pretrained_bert, do_lower_case='uncased' in opt.pretrained_bert)
        self.max_seq_len = max_seq_len

    def text_to_sequence(self, text, reverse=False, padding='post', truncating='post'):
        # sequence = self.tokenizer.convert_tokens_to_ids(self.tokenizer.tokenize(text))
        # if len(sequence) == 0:
        #     sequence = [0]
        # if reverse:
        #     sequence = sequence[::-1]
        # return pad_and_truncate(sequence, self.max_seq_len, padding=padding, truncating=truncating)
        return self.tokenizer.encode(text, truncation=True, padding='max_length', max_length=self.max_seq_len, return_tensors='pt')


class TADBERTTCDataset(Dataset):

    def __init__(self, tokenizer, opt):
        self.bert_baseline_input_colses = {
            'bert': ['text_bert_indices']
        }

        self.tokenizer = tokenizer
        self.opt = opt
        self.all_data = []

    def parse_sample(self, text):
        return [text]

    def prepare_infer_sample(self, text: str, ignore_error):
        self.process_data(self.parse_sample(text), ignore_error=ignore_error)

    def prepare_infer_dataset(self, infer_file, ignore_error):

        lines = load_apc_datasets(infer_file)
        samples = []
        for sample in lines:
            if sample:
                samples.extend(self.parse_sample(sample))
        self.process_data(samples, ignore_error)

    def process_data(self, samples, ignore_error=True):
        all_data = []
        if len(samples) > 100:
            it = tqdm.tqdm(samples, postfix='preparing text classification inference dataloader...')
        else:
            it = samples
        for text in it:
            try:
                # handle for empty lines in inference datasets
                if text is None or '' == text.strip():
                    raise RuntimeError('Invalid Input!')

                if '!ref!' in text:
                    text, _, labels = text.strip().partition('!ref!')
                    text = text.strip()
                    label, perturb_label, is_adv = labels.strip().split(',')
                    label, perturb_label, is_adv = label.strip(), perturb_label.strip(), is_adv.strip()

                    # label = -100
                else:
                    text = text.strip()
                    label = -100
                    perturb_label = -100
                    is_adv = -100

                # if label == perturb_label:
                #     continue

                if is_adv == '1' or is_adv == 1:
                    label = '-100'

                text_indices = self.tokenizer.text_to_sequence('{}'.format(text))

                data = {
                    'text_bert_indices': text_indices[0],

                    'text_raw': text,

                    'label': label,

                    'perturb_label': perturb_label,

                    'is_adv': is_adv,
                    # 'label': self.opt.label_to_index.get(label, -100) if isinstance(label, str) else label,
                    #
                    # 'perturb_label': self.opt.perturb_label_to_index.get(perturb_label, -100) if isinstance(perturb_label, str) else perturb_label,
                    #
                    # 'is_adv': self.opt.is_adv_to_index.get(is_adv, -100) if isinstance(is_adv, str) else is_adv,
                }

                all_data.append(data)

            except Exception as e:
                if ignore_error:
                    print('Ignore error while processing:', text)
                else:
                    raise e

        self.all_data = all_data
        return self.all_data

    def __getitem__(self, index):
        return self.all_data[index]

    def __len__(self):
        return len(self.all_data)