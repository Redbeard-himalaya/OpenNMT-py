#!/usr/bin/env python
# flake8: noqa
import json
import torch
import argparse
import pyonmttok
from argparse import Namespace
from onmt.inputters.inputter import vocabs_to_dict
from onmt.constants import DefaultTokens
from sentencepiece import SentencePieceProcessor
import os
from transformers import AutoModelForCausalLM


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model_dir", type=str, required=True, help="""Path to the model directory"""
    )
    parser.add_argument(
        "--vocab_file", type=str, required=True, help="""Path to the tokenizer model"""
    )
    parser.add_argument(
        "--output", type=str, required=True, help="""Path to the model directory"""
    )
    opt = parser.parse_args()

    model = AutoModelForCausalLM.from_pretrained(
        opt.model_dir,
        torch_dtype=torch.float16,
        device_map={"": "cpu"},
        trust_remote_code=True,
    )
    checkpoint = model.state_dict()

    params_json = os.path.join(opt.model_dir, "config.json")
    with open(params_json, encoding="utf-8") as fparam:
        params = json.load(fparam)

    onmt_cp = {}
    onmt_cp["model"] = {}

    decoder_layers = params["n_layers"]
    src_word_vec_size = params["d_model"]
    tgt_word_vec_size = params["d_model"]
    hidden_size = params["d_model"]
    heads = params["n_heads"]
    vocab_size = params["vocab_size"]
    transformer_ff = params["expansion_ratio"] * params["d_model"]

    onmt_cp["model"][
        "decoder.embeddings.make_embedding.emb_luts.0.weight"
    ] = checkpoint["transformer.wte.weight"]

    for i in range(decoder_layers):
        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".self_attn.linear_query.weight"
        ] = checkpoint["transformer.blocks." + str(i) + ".attn.Wqkv.weight"][
            :hidden_size, :
        ]

        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".self_attn.linear_keys.weight"
        ] = checkpoint["transformer.blocks." + str(i) + ".attn.Wqkv.weight"][
            hidden_size : (hidden_size * 2), :
        ]

        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".self_attn.linear_values.weight"
        ] = checkpoint["transformer.blocks." + str(i) + ".attn.Wqkv.weight"][
            (hidden_size * 2) :, :
        ]

        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".self_attn.final_linear.weight"
        ] = checkpoint["transformer.blocks." + str(i) + ".attn.out_proj.weight"]

        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".layer_norm_1.weight"
        ] = checkpoint["transformer.blocks." + str(i) + ".norm_1.weight"]
        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".layer_norm_1.bias"
        ] = torch.zeros(
            onmt_cp["model"][
                "decoder.transformer_layers." + str(i) + ".layer_norm_1.weight"
            ].size(0),
            dtype=torch.float16,
        )

        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".feed_forward.w_1.weight"
        ] = checkpoint["transformer.blocks." + str(i) + ".ffn.up_proj.weight"]
        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".feed_forward.w_1.bias"
        ] = torch.zeros(
            onmt_cp["model"][
                "decoder.transformer_layers." + str(i) + ".feed_forward.w_1.weight"
            ].size(0),
            dtype=torch.float16,
        )

        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".feed_forward.w_2.weight"
        ] = checkpoint["transformer.blocks." + str(i) + ".ffn.down_proj.weight"]
        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".feed_forward.w_2.bias"
        ] = torch.zeros(
            onmt_cp["model"][
                "decoder.transformer_layers." + str(i) + ".feed_forward.w_2.weight"
            ].size(0),
            dtype=torch.float16,
        )

        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".feed_forward.layer_norm.weight"
        ] = checkpoint["transformer.blocks." + str(i) + ".norm_2.weight"]
        onmt_cp["model"][
            "decoder.transformer_layers." + str(i) + ".feed_forward.layer_norm.bias"
        ] = torch.zeros(
            onmt_cp["model"][
                "decoder.transformer_layers."
                + str(i)
                + ".feed_forward.layer_norm.weight"
            ].size(0),
            dtype=torch.float16,
        )

    onmt_cp["model"]["decoder.layer_norm.weight"] = checkpoint[
        "transformer.norm_f.weight"
    ]
    onmt_cp["model"]["decoder.layer_norm.bias"] = torch.zeros(
        onmt_cp["model"]["decoder.layer_norm.weight"].size(0), dtype=torch.float16
    )

    onmt_cp["generator"] = {}
    onmt_cp["generator"]["weight"] = checkpoint["transformer.wte.weight"]
    onmt_cp["generator"]["bias"] = torch.zeros(
        onmt_cp["generator"]["weight"].size(0), dtype=torch.float16
    )

    vocabs = {}
    with open(opt.vocab_file, "r", encoding="utf-8") as vocab:
        src_vocab = pyonmttok.build_vocab_from_lines(vocab)

    vocabs["src"] = src_vocab
    vocabs["tgt"] = src_vocab
    vocabs["data_task"] = "lm"
    vocabs["decoder_start_token"] = "</s>"

    onmt_cp["vocab"] = {}
    onmt_cp["vocab"] = vocabs_to_dict(vocabs)

    onmt_cp["opt"] = Namespace(
        config=None,
        save_config=None,
        data={},
        skip_empty_level="silent",
        save_data=None,
        overwrite=False,
        n_sample=0,
        dump_transforms=False,
        src_vocab=None,
        tgt_vocab=None,
        share_vocab=True,
        src_feats_vocab=None,
        src_vocab_size=vocab_size,
        tgt_vocab_size=vocab_size,
        vocab_size_multiple=8,
        src_words_min_frequency=0,
        tgt_words_min_frequency=0,
        decoder_start_token=vocabs["decoder_start_token"],
        src_seq_length_trunc=None,
        tgt_seq_length_trunc=None,
        both_embeddings=None,
        src_embeddings=None,
        tgt_embeddings=None,
        embeddings_type=None,
        switchout_temperature=1.0,
        tokendrop_temperature=1.0,
        tokenmask_temperature=1.0,
        reversible_tokenization=None,
        prior_tokenization=False,
        src_subword_model=None,
        tgt_subword_model=None,
        src_subword_nbest=1,
        tgt_subword_nbest=1,
        src_subword_alpha=0.0,
        tgt_subword_alpha=0.0,
        src_subword_vocab="",
        tgt_subword_vocab="",
        src_vocab_threshold=0,
        tgt_vocab_threshold=0,
        src_subword_type="none",
        tgt_subword_type="none",
        src_onmttok_kwargs="{'mode': 'none'}",
        tgt_onmttok_kwargs="{'mode': 'none'}",
        src_seq_length=512,
        tgt_seq_length=512,
        src_prefix="",
        tgt_prefix="",
        permute_sent_ratio=0.0,
        rotate_ratio=0.0,
        insert_ratio=0.0,
        random_ratio=0.0,
        mask_ratio=0.0,
        mask_length="subword",
        poisson_lambda=3.0,
        replace_length=-1,
        src_word_vec_size=src_word_vec_size,
        tgt_word_vec_size=tgt_word_vec_size,
        word_vec_size=src_word_vec_size,
        share_decoder_embeddings=False,
        share_embeddings=False,
        position_encoding=False,
        update_vocab=False,
        feat_merge="concat",
        feat_vec_size=-1,
        feat_vec_exponent=0.7,
        model_task="lm",
        model_type="text",
        model_dtype="fp16",
        encoder_type="transformer_lm",
        decoder_type="transformer_lm",
        freeze_encoder=False,
        freeze_decoder=False,
        layers=-1,
        dec_layers=decoder_layers,
        hidden_size=hidden_size,
        enc_hid_size=hidden_size,
        dec_hid_size=hidden_size,
        cnn_kernel_width=3,
        layer_norm="standard",
        pos_ffn_activation_fn="gelu",
        input_feed=1,
        bridge=False,
        rnn_type="LSTM",
        context_gate=None,
        bridge_extra_node=True,
        bidir_edges=True,
        state_dim=512,
        n_edge_types=2,
        n_node=2,
        n_steps=2,
        src_ggnn_size=0,
        global_attention="general",
        global_attention_function="softmax",
        self_attn_type="scaled-dot",
        max_relative_positions=-2,
        heads=heads,
        transformer_ff=transformer_ff,
        aan_useffn=False,
        add_qkvbias=False,
        lambda_align=0.0,
        alignment_layer=-3,
        alignment_heads=0,
        full_context_alignment=False,
        copy_attn=False,
        copy_attn_type="general",
        generator_function="softmax",
        copy_attn_force=False,
        reuse_copy_attn=False,
        copy_loss_by_seqlength=False,
        coverage_attn=False,
        lambda_coverage=0.0,
        lm_prior_model=None,
        lm_prior_lambda=0.0,
        lm_prior_tau=1.0,
        loss_scale=0,
        apex_opt_level="",
        data_type="text",
        save_model=None,
        save_checkpoint_steps=5000,
        keep_checkpoint=50,
        gpu_ranks=[0],
        world_size=1,
        gpu_backend="nccl",
        gpu_verbose_level=0,
        master_ip="localhost",
        master_port=10000,
        seed=1234,
        param_init=0.0,
        param_init_glorot=True,
        train_from=None,
        reset_optim="none",
        pre_word_vecs_enc=None,
        pre_word_vecs_dec=None,
        freeze_word_vecs_enc=False,
        freeze_word_vecs_dec=False,
        num_workers=2,
        batch_size=896,
        batch_size_multiple=1,
        batch_type="tokens",
        normalization="tokens",
        accum_count=[32],
        accum_steps=[0],
        valid_steps=400,
        valid_batch_size=256,
        train_steps=4000,
        single_pass=False,
        early_stopping=0,
        early_stopping_criteria=None,
        optim="fusedadam",
        adagrad_accumulator_init=0,
        max_grad_norm=0.0,
        dropout=[0.0],
        attention_dropout=[0.0],
        dropout_steps=[0],
        truncated_decoder=0,
        adam_beta1=0.9,
        adam_beta2=0.998,
        label_smoothing=0.0,
        average_decay=0,
        average_every=1,
        learning_rate=0.00002,
        learning_rate_decay=0.5,
        start_decay_steps=50000,
        decay_steps=10000,
        decay_method="none",
        warmup_steps=4000,
        log_file="",
        log_file_level="0",
        verbose=False,
        train_eval_steps=200,
        train_metrics=[],
        valid_metrics=[],
        scoring_debug=False,
        dump_preds=None,
        report_every=100,
        exp_host="",
        exp="",
        tensorboard=False,
        tensorboard_log_dir="runs/onmt",
        bucket_size=262144,
        bucket_size_init=-1,
        bucket_size_increment=0,
        prefetch_factor=400,
        brnn=False,
        data_task="lm",
        _all_transform={"filtertoolong"},
    )

    totalsize = 0
    for m in ["model", "generator"]:
        for item in onmt_cp[m].keys():
            item2 = onmt_cp[m][item]
            totalsize += item2.nelement() * item2.element_size()
    print("Saving parameters: ", totalsize)

    torch.save(onmt_cp, opt.output)
