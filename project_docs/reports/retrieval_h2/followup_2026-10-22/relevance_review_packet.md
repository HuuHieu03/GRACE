# H2 single-demonstration relevance packet

Assess each query/demo using rubric.md. Scores, source labels and policy are withheld.

## H2R-001

### Query

```c

vmxnet3_pop_next_tx_descr(VMXNET3State *s,

                          int qidx,

                          struct Vmxnet3_TxDesc *txd,

                          uint32_t *descr_idx)

{

    Vmxnet3Ring *ring = &s->txq_descr[qidx].tx_ring;

    PCIDevice *d = PCI_DEVICE(s);



    vmxnet3_ring_read_curr_cell(d, ring, txd);

    if (txd->gen == vmxnet3_ring_curr_gen(ring)) {

        /* Only read after generation field verification */

        smp_rmb();

        /* Re-read to be sure we got the latest version */

        vmxnet3_ring_read_curr_cell(d, ring, txd);

        VMXNET3_RING_DUMP(VMW_RIPRN, "TX", qidx, ring);

        *descr_idx = vmxnet3_ring_curr_cell_idx(ring);

        vmxnet3_inc_tx_consumption_counter(s, qidx);

        return true;

    }



    return false;

}

```

### Demonstration

```c

int vp78_decode_mb_row_sliced(AVCodecContext *avctx, void *tdata, int jobnr,

                              int threadnr, int is_vp7)

{

    VP8Context *s = avctx->priv_data;

    VP8ThreadData *td = &s->thread_data[jobnr];

    VP8ThreadData *next_td = NULL, *prev_td = NULL;

    VP8Frame *curframe = s->curframe;

    int mb_y, num_jobs = s->num_jobs;

    int ret;



    td->thread_nr = threadnr;

    for (mb_y = jobnr; mb_y < s->mb_height; mb_y += num_jobs) {

        atomic_store(&td->thread_mb_pos, mb_y << 16);

        ret = s->decode_mb_row_no_filter(avctx, tdata, jobnr, threadnr);

        if (ret < 0) {

            update_pos(td, s->mb_height, INT_MAX & 0xFFFF);

            return ret;

        }

        if (s->deblock_filter)

            s->filter_mb_row(avctx, tdata, jobnr, threadnr);

        update_pos(td, mb_y, INT_MAX & 0xFFFF);



        s->mv_min.y -= 64;

        s->mv_max.y -= 64;



        if (avctx->active_thread_type == FF_THREAD_FRAME)

            ff_thread_report_progress(&curframe->tf, mb_y, 0);

    }



    return 0;

}

```

## H2R-002

### Query

```c

static int mxf_read_content_storage(MXFContext *mxf, ByteIOContext *pb, int tag)

{

    switch (tag) {

    case 0x1901:

        mxf->packages_count = get_be32(pb);

        if (mxf->packages_count >= UINT_MAX / sizeof(UID))

            return -1;

        mxf->packages_refs = av_malloc(mxf->packages_count * sizeof(UID));

        if (!mxf->packages_refs)

            return -1;

        url_fskip(pb, 4); /* useless size of objects, always 16 according to specs */

        get_buffer(pb, (uint8_t *)mxf->packages_refs, mxf->packages_count * sizeof(UID));

        break;

    }

    return 0;

}

```

### Demonstration

```c

static int mxf_read_material_package(MXFPackage *package, ByteIOContext *pb, int tag)

{

    switch(tag) {

    case 0x4403:

        package->tracks_count = get_be32(pb);

        if (package->tracks_count >= UINT_MAX / sizeof(UID))

            return -1;

        package->tracks_refs = av_malloc(package->tracks_count * sizeof(UID));

        if (!package->tracks_refs)

            return -1;

        url_fskip(pb, 4); /* useless size of objects, always 16 according to specs */

        get_buffer(pb, (uint8_t *)package->tracks_refs, package->tracks_count * sizeof(UID));

        break;

    }

    return 0;

}

```

## H2R-003

### Query

```c

static void tcg_liveness_analysis(TCGContext *s)

{

    uint8_t *dead_temps, *mem_temps;

    int oi, oi_prev, nb_ops;



    nb_ops = s->gen_next_op_idx;

    s->op_dead_args = tcg_malloc(nb_ops * sizeof(uint16_t));

    s->op_sync_args = tcg_malloc(nb_ops * sizeof(uint8_t));

    

    dead_temps = tcg_malloc(s->nb_temps);

    mem_temps = tcg_malloc(s->nb_temps);

    tcg_la_func_end(s, dead_temps, mem_temps);



    for (oi = s->gen_last_op_idx; oi >= 0; oi = oi_prev) {

        int i, nb_iargs, nb_oargs;

        TCGOpcode opc_new, opc_new2;

        bool have_opc_new2;

        uint16_t dead_args;

        uint8_t sync_args;

        TCGArg arg;



        TCGOp * const op = &s->gen_op_buf[oi];

        TCGArg * const args = &s->gen_opparam_buf[op->args];

        TCGOpcode opc = op->opc;

        const TCGOpDef *def = &tcg_op_defs[opc];



        oi_prev = op->prev;



        switch (opc) {

        case INDEX_op_call:

            {

                int call_flags;



                nb_oargs = op->callo;

                nb_iargs = op->calli;

                call_flags = args[nb_oargs + nb_iargs + 1];



                /* pure functions can be removed if their result is unused */

                if (call_flags & TCG_CALL_NO_SIDE_EFFECTS) {

                    for (i = 0; i < nb_oargs; i++) {

                        arg = args[i];

                        if (!dead_temps[arg] || mem_temps[arg]) {

                            goto do_not_remove_call;

                        }

                    }

                    goto do_remove;

                } else {

                do_not_remove_call:



                    /* output args are dead */

                    dead_args = 0;

                    sync_args = 0;

                    for (i = 0; i < nb_oargs; i++) {

                        arg = args[i];

                        if (dead_temps[arg]) {

                            dead_args |= (1 << i);

                        }

                        if (mem_temps[arg]) {

                            sync_args |= (1 << i);

                        }

                        dead_temps[arg] = 1;

                        mem_temps[arg] = 0;

                    }



                    if (!(call_flags & TCG_CALL_NO_READ_GLOBALS)) {

                        /* globals should be synced to memory */

                        memset(mem_temps, 1, s->nb_globals);

                    }

                    if (!(call_flags & (TCG_CALL_NO_WRITE_GLOBALS |

                                        TCG_CALL_NO_READ_GLOBALS))) {

                        /* globals should go back to memory */

                        memset(dead_temps, 1, s->nb_globals);

                    }



                    /* input args are live */

                    for (i = nb_oargs; i < nb_iargs + nb_oargs; i++) {

                        arg = args[i];

                        if (arg != TCG_CALL_DUMMY_ARG) {

                            if (dead_temps[arg]) {

                                dead_args |= (1 << i);

                            }

                            dead_temps[arg] = 0;

                        }

                    }

                    s->op_dead_args[oi] = dead_args;

                    s->op_sync_args[oi] = sync_args;

                }

            }

            break;

        case INDEX_op_debug_insn_start:

            break;

        case INDEX_op_discard:

            /* mark the temporary as dead */

            dead_temps[args[0]] = 1;

            mem_temps[args[0]] = 0;

            break;



        case INDEX_op_add2_i32:

            opc_new = INDEX_op_add_i32;

            goto do_addsub2;

        case INDEX_op_sub2_i32:

            opc_new = INDEX_op_sub_i32;

            goto do_addsub2;

        case INDEX_op_add2_i64:

            opc_new = INDEX_op_add_i64;

            goto do_addsub2;

        case INDEX_op_sub2_i64:

            opc_new = INDEX_op_sub_i64;

        do_addsub2:

            nb_iargs = 4;

            nb_oargs = 2;

            /* Test if the high part of the operation is dead, but not

               the low part.  The result can be optimized to a simple

               add or sub.  This happens often for x86_64 guest when the

               cpu mode is set to 32 bit.  */

            if (dead_temps[args[1]] && !mem_temps[args[1]]) {

                if (dead_temps[args[0]] && !mem_temps[args[0]]) {

                    goto do_remove;

                }

                /* Replace the opcode and adjust the args in place,

                   leaving 3 unused args at the end.  */

                op->opc = opc = opc_new;

                args[1] = args[2];

                args[2] = args[4];

                /* Fall through and mark the single-word operation live.  */

                nb_iargs = 2;

                nb_oargs = 1;

            }

            goto do_not_remove;



        case INDEX_op_mulu2_i32:

            opc_new = INDEX_op_mul_i32;

            opc_new2 = INDEX_op_muluh_i32;

            have_opc_new2 = TCG_TARGET_HAS_muluh_i32;

            goto do_mul2;

        case INDEX_op_muls2_i32:

            opc_new = INDEX_op_mul_i32;

            opc_new2 = INDEX_op_mulsh_i32;

            have_opc_new2 = TCG_TARGET_HAS_mulsh_i32;

            goto do_mul2;

        case INDEX_op_mulu2_i64:

            opc_new = INDEX_op_mul_i64;

            opc_new2 = INDEX_op_muluh_i64;

            have_opc_new2 = TCG_TARGET_HAS_muluh_i64;

            goto do_mul2;

        case INDEX_op_muls2_i64:

            opc_new = INDEX_op_mul_i64;

            opc_new2 = INDEX_op_mulsh_i64;

            have_opc_new2 = TCG_TARGET_HAS_mulsh_i64;

            goto do_mul2;

        do_mul2:

            nb_iargs = 2;

            nb_oargs = 2;

            if (dead_temps[args[1]] && !mem_temps[args[1]]) {

                if (dead_temps[args[0]] && !mem_temps[args[0]]) {

                    /* Both parts of the operation are dead.  */

                    goto do_remove;

                }

                /* The high part of the operation is dead; generate the low. */

                op->opc = opc = opc_new;

                args[1] = args[2];

                args[2] = args[3];

            } else if (have_opc_new2 && dead_temps[args[0]]

                       && !mem_temps[args[0]]) {

                /* The low part of the operation is dead; generate the high. */

                op->opc = opc = opc_new2;

                args[0] = args[1];

                args[1] = args[2];

                args[2] = args[3];

            } else {

                goto do_not_remove;

            }

            /* Mark the single-word operation live.  */

            nb_oargs = 1;

            goto do_not_remove;



        default:

            /* XXX: optimize by hardcoding common cases (e.g. triadic ops) */

            nb_iargs = def->nb_iargs;

            nb_oargs = def->nb_oargs;



            /* Test if the operation can be removed because all

               its outputs are dead. We assume that nb_oargs == 0

               implies side effects */

            if (!(def->flags & TCG_OPF_SIDE_EFFECTS) && nb_oargs != 0) {

                for (i = 0; i < nb_oargs; i++) {

                    arg = args[i];

                    if (!dead_temps[arg] || mem_temps[arg]) {

                        goto do_not_remove;

                    }

                }

            do_remove:

                tcg_op_remove(s, op);

            } else {

            do_not_remove:

                /* output args are dead */

                dead_args = 0;

                sync_args = 0;

                for (i = 0; i < nb_oargs; i++) {

                    arg = args[i];

                    if (dead_temps[arg]) {

                        dead_args |= (1 << i);

                    }

                    if (mem_temps[arg]) {

                        sync_args |= (1 << i);

                    }

                    dead_temps[arg] = 1;

                    mem_temps[arg] = 0;

                }



                /* if end of basic block, update */

                if (def->flags & TCG_OPF_BB_END) {

                    tcg_la_bb_end(s, dead_temps, mem_temps);

                } else if (def->flags & TCG_OPF_SIDE_EFFECTS) {

                    /* globals should be synced to memory */

                    memset(mem_temps, 1, s->nb_globals);

                }



                /* input args are live */

                for (i = nb_oargs; i < nb_oargs + nb_iargs; i++) {

                    arg = args[i];

                    if (dead_temps[arg]) {

                        dead_args |= (1 << i);

                    }

                    dead_temps[arg] = 0;

                }

                s->op_dead_args[oi] = dead_args;

                s->op_sync_args[oi] = sync_args;

            }

            break;

        }

    }

}

```

### Demonstration

```c

void tcg_gen_callN(void *func, TCGTemp *ret, int nargs, TCGTemp **args)

{

    TCGContext *s = tcg_ctx;

    int i, real_args, nb_rets, pi;

    unsigned sizemask, flags;

    TCGHelperInfo *info;

    TCGOp *op;



    info = g_hash_table_lookup(helper_table, (gpointer)func);

    flags = info->flags;

    sizemask = info->sizemask;



#if defined(__sparc__) && !defined(__arch64__) \

    && !defined(CONFIG_TCG_INTERPRETER)

    /* We have 64-bit values in one register, but need to pass as two

       separate parameters.  Split them.  */

    int orig_sizemask = sizemask;

    int orig_nargs = nargs;

    TCGv_i64 retl, reth;

    TCGTemp *split_args[MAX_OPC_PARAM];



    retl = NULL;

    reth = NULL;

    if (sizemask != 0) {

        for (i = real_args = 0; i < nargs; ++i) {

            int is_64bit = sizemask & (1 << (i+1)*2);

            if (is_64bit) {

                TCGv_i64 orig = temp_tcgv_i64(args[i]);

                TCGv_i32 h = tcg_temp_new_i32();

                TCGv_i32 l = tcg_temp_new_i32();

                tcg_gen_extr_i64_i32(l, h, orig);

                split_args[real_args++] = tcgv_i32_temp(h);

                split_args[real_args++] = tcgv_i32_temp(l);

            } else {

                split_args[real_args++] = args[i];

            }

        }

        nargs = real_args;

        args = split_args;

        sizemask = 0;

    }

#elif defined(TCG_TARGET_EXTEND_ARGS) && TCG_TARGET_REG_BITS == 64

    for (i = 0; i < nargs; ++i) {

        int is_64bit = sizemask & (1 << (i+1)*2);

        int is_signed = sizemask & (2 << (i+1)*2);

        if (!is_64bit) {

            TCGv_i64 temp = tcg_temp_new_i64();

            TCGv_i64 orig = temp_tcgv_i64(args[i]);

            if (is_signed) {

                tcg_gen_ext32s_i64(temp, orig);

            } else {

                tcg_gen_ext32u_i64(temp, orig);

            }

            args[i] = tcgv_i64_temp(temp);

        }

    }

#endif /* TCG_TARGET_EXTEND_ARGS */



    i = s->gen_next_op_idx;

    tcg_debug_assert(i < OPC_BUF_SIZE);

    s->gen_op_buf[0].prev = i;

    s->gen_next_op_idx = i + 1;

    op = &s->gen_op_buf[i];



    /* Set links for sequential allocation during translation.  */

    memset(op, 0, offsetof(TCGOp, args));

    op->opc = INDEX_op_call;

    op->prev = i - 1;

    op->next = i + 1;



    pi = 0;

    if (ret != NULL) {

#if defined(__sparc__) && !defined(__arch64__) \

    && !defined(CONFIG_TCG_INTERPRETER)

        if (orig_sizemask & 1) {

            /* The 32-bit ABI is going to return the 64-bit value in

               the %o0/%o1 register pair.  Prepare for this by using

               two return temporaries, and reassemble below.  */

            retl = tcg_temp_new_i64();

            reth = tcg_temp_new_i64();

            op->args[pi++] = tcgv_i64_arg(reth);

            op->args[pi++] = tcgv_i64_arg(retl);

            nb_rets = 2;

        } else {

            op->args[pi++] = temp_arg(ret);

            nb_rets = 1;

        }

#else

        if (TCG_TARGET_REG_BITS < 64 && (sizemask & 1)) {

#ifdef HOST_WORDS_BIGENDIAN

            op->args[pi++] = temp_arg(ret + 1);

            op->args[pi++] = temp_arg(ret);

#else

            op->args[pi++] = temp_arg(ret);

            op->args[pi++] = temp_arg(ret + 1);

#endif

            nb_rets = 2;

        } else {

            op->args[pi++] = temp_arg(ret);

            nb_rets = 1;

        }

#endif

    } else {

        nb_rets = 0;

    }

    op->callo = nb_rets;



    real_args = 0;

    for (i = 0; i < nargs; i++) {

        int is_64bit = sizemask & (1 << (i+1)*2);

        if (TCG_TARGET_REG_BITS < 64 && is_64bit) {

#ifdef TCG_TARGET_CALL_ALIGN_ARGS

            /* some targets want aligned 64 bit args */

            if (real_args & 1) {

                op->args[pi++] = TCG_CALL_DUMMY_ARG;

                real_args++;

            }

#endif

           /* If stack grows up, then we will be placing successive

              arguments at lower addresses, which means we need to

              reverse the order compared to how we would normally

              treat either big or little-endian.  For those arguments

              that will wind up in registers, this still works for

              HPPA (the only current STACK_GROWSUP target) since the

              argument registers are *also* allocated in decreasing

              order.  If another such target is added, this logic may

              have to get more complicated to differentiate between

              stack arguments and register arguments.  */

#if defined(HOST_WORDS_BIGENDIAN) != defined(TCG_TARGET_STACK_GROWSUP)

            op->args[pi++] = temp_arg(args[i] + 1);

            op->args[pi++] = temp_arg(args[i]);

#else

            op->args[pi++] = temp_arg(args[i]);

            op->args[pi++] = temp_arg(args[i] + 1);

#endif

            real_args += 2;

            continue;

        }



        op->args[pi++] = temp_arg(args[i]);

        real_args++;

    }

    op->args[pi++] = (uintptr_t)func;

    op->args[pi++] = flags;

    op->calli = real_args;



    /* Make sure the fields didn't overflow.  */

    tcg_debug_assert(op->calli == real_args);

    tcg_debug_assert(pi <= ARRAY_SIZE(op->args));



#if defined(__sparc__) && !defined(__arch64__) \

    && !defined(CONFIG_TCG_INTERPRETER)

    /* Free all of the parts we allocated above.  */

    for (i = real_args = 0; i < orig_nargs; ++i) {

        int is_64bit = orig_sizemask & (1 << (i+1)*2);

        if (is_64bit) {

            tcg_temp_free_internal(args[real_args++]);

            tcg_temp_free_internal(args[real_args++]);

        } else {

            real_args++;

        }

    }

    if (orig_sizemask & 1) {

        /* The 32-bit ABI returned two 32-bit pieces.  Re-assemble them.

           Note that describing these as TCGv_i64 eliminates an unnecessary

           zero-extension that tcg_gen_concat_i32_i64 would create.  */

        tcg_gen_concat32_i64(temp_tcgv_i64(ret), retl, reth);

        tcg_temp_free_i64(retl);

        tcg_temp_free_i64(reth);

    }

#elif defined(TCG_TARGET_EXTEND_ARGS) && TCG_TARGET_REG_BITS == 64

    for (i = 0; i < nargs; ++i) {

        int is_64bit = sizemask & (1 << (i+1)*2);

        if (!is_64bit) {

            tcg_temp_free_internal(args[i]);

        }

    }

#endif /* TCG_TARGET_EXTEND_ARGS */

}

```

## H2R-004

### Query

```c

static void handle_user_command(Monitor *mon, const char *cmdline)

{

    QDict *qdict;

    const mon_cmd_t *cmd;



    qdict = qdict_new();



    cmd = monitor_parse_command(mon, cmdline, 0, mon->cmd_table, qdict);

    if (!cmd)

        goto out;



    if (handler_is_async(cmd)) {

        user_async_cmd_handler(mon, cmd, qdict);

    } else if (handler_is_qobject(cmd)) {

        QObject *data = NULL;



        /* XXX: ignores the error code */

        cmd->mhandler.cmd_new(mon, qdict, &data);

        assert(!monitor_has_error(mon));

        if (data) {

            cmd->user_print(mon, data);

            qobject_decref(data);

        }

    } else {

        cmd->mhandler.cmd(mon, qdict);

    }



out:

    QDECREF(qdict);

}

```

### Demonstration

```c

static void handle_user_command(Monitor *mon, const char *cmdline)

{

    QDict *qdict;

    const mon_cmd_t *cmd;



    qdict = qdict_new();



    cmd = monitor_parse_command(mon, cmdline, qdict);

    if (!cmd)

        goto out;



    if (monitor_handler_is_async(cmd)) {

        user_async_cmd_handler(mon, cmd, qdict);

    } else if (monitor_handler_ported(cmd)) {

        monitor_call_handler(mon, cmd, qdict);

    } else {

        cmd->mhandler.cmd(mon, qdict);

    }



    if (monitor_has_error(mon))

        monitor_print_error(mon);



out:

    QDECREF(qdict);

}

```

## H2R-005

### Query

```c

int av_reallocp_array(void *ptr, size_t nmemb, size_t size)

{

    void **ptrptr = ptr;

    void *ret;

    if (size <= 0 || nmemb >= INT_MAX / size)

        return AVERROR(ENOMEM);

    if (nmemb <= 0) {

        av_freep(ptr);

        return 0;

    }

    ret = av_realloc(*ptrptr, nmemb * size);

    if (!ret) {

        av_freep(ptr);

        return AVERROR(ENOMEM);

    }

    *ptrptr = ret;

    return 0;

}

```

### Demonstration

```c

static int set_string_binary(void *obj, const AVOption *o, const char *val, uint8_t **dst)

{

    int *lendst = (int *)(dst + 1);

    uint8_t *bin, *ptr;

    int len = strlen(val);



    av_freep(dst);

    *lendst = 0;



    if (len & 1)

        return AVERROR(EINVAL);

    len /= 2;



    ptr = bin = av_malloc(len);

    while (*val) {

        int a = hexchar2int(*val++);

        int b = hexchar2int(*val++);

        if (a < 0 || b < 0) {

            av_free(bin);

            return AVERROR(EINVAL);

        }

        *ptr++ = (a << 4) | b;

    }

    *dst = bin;

    *lendst = len;



    return 0;

}

```

## H2R-006

### Query

```c

static int dx2_decode_slice_410(GetBitContext *gb, AVFrame *frame,

                                int line, int left,

                                uint8_t lru[3][8])

{

    int x, y, i, j;

    int width   = frame->width;



    int ystride = frame->linesize[0];

    int ustride = frame->linesize[1];

    int vstride = frame->linesize[2];



    uint8_t *Y  = frame->data[0] + ystride * line;

    uint8_t *U  = frame->data[1] + (ustride >> 2) * line;

    uint8_t *V  = frame->data[2] + (vstride >> 2) * line;



    for (y = 0; y < left - 3 && get_bits_left(gb) > 16; y += 4) {

        for (x = 0; x < width; x += 4) {

            for (j = 0; j < 4; j++)

                for (i = 0; i < 4; i++)

                    Y[x + i + j * ystride] = decode_sym(gb, lru[0]);

            U[x >> 2] = decode_sym(gb, lru[1]) ^ 0x80;

            V[x >> 2] = decode_sym(gb, lru[2]) ^ 0x80;

        }



        Y += ystride << 2;

        U += ustride;

        V += vstride;

    }



    return y;

}

```

### Demonstration

```c

static int dx2_decode_slice_420(GetBitContext *gb, AVFrame *frame,

                                int line, int left,

                                uint8_t lru[3][8])

{

    int x, y;



    int width    = frame->width;



    int ystride = frame->linesize[0];

    int ustride = frame->linesize[1];

    int vstride = frame->linesize[2];



    uint8_t *Y  = frame->data[0] + ystride * line;

    uint8_t *U  = frame->data[1] + (ustride >> 1) * line;

    uint8_t *V  = frame->data[2] + (vstride >> 1) * line;





    for (y = 0; y < left - 1 && get_bits_left(gb) > 16; y += 2) {

        for (x = 0; x < width; x += 2) {

            Y[x + 0 + 0 * ystride] = decode_sym(gb, lru[0]);

            Y[x + 1 + 0 * ystride] = decode_sym(gb, lru[0]);

            Y[x + 0 + 1 * ystride] = decode_sym(gb, lru[0]);

            Y[x + 1 + 1 * ystride] = decode_sym(gb, lru[0]);

            U[x >> 1] = decode_sym(gb, lru[1]) ^ 0x80;

            V[x >> 1] = decode_sym(gb, lru[2]) ^ 0x80;

        }



        Y += ystride << 1;

        U += ustride;

        V += vstride;

    }



    return y;

}

```

## H2R-007

### Query

```c

static uint64_t sp804_read(void *opaque, target_phys_addr_t offset,

                           unsigned size)

{

    sp804_state *s = (sp804_state *)opaque;



    if (offset < 0x20) {

        return arm_timer_read(s->timer[0], offset);

    }

    if (offset < 0x40) {

        return arm_timer_read(s->timer[1], offset - 0x20);

    }



    /* TimerPeriphID */

    if (offset >= 0xfe0 && offset <= 0xffc) {

        return sp804_ids[(offset - 0xfe0) >> 2];

    }



    switch (offset) {

    /* Integration Test control registers, which we won't support */

    case 0xf00: /* TimerITCR */

    case 0xf04: /* TimerITOP (strictly write only but..) */

        return 0;

    }



    hw_error("%s: Bad offset %x\n", __func__, (int)offset);

    return 0;

}

```

### Demonstration

```c

static uint64_t pl050_read(void *opaque, hwaddr offset,

                           unsigned size)

{

    pl050_state *s = (pl050_state *)opaque;

    if (offset >= 0xfe0 && offset < 0x1000)

        return pl050_id[(offset - 0xfe0) >> 2];



    switch (offset >> 2) {

    case 0: /* KMICR */

        return s->cr;

    case 1: /* KMISTAT */

        {

            uint8_t val;

            uint32_t stat;



            val = s->last;

            val = val ^ (val >> 4);

            val = val ^ (val >> 2);

            val = (val ^ (val >> 1)) & 1;



            stat = PL050_TXEMPTY;

            if (val)

                stat |= PL050_RXPARITY;

            if (s->pending)

                stat |= PL050_RXFULL;



            return stat;

        }

    case 2: /* KMIDATA */

        if (s->pending)

            s->last = ps2_read_data(s->dev);

        return s->last;

    case 3: /* KMICLKDIV */

        return s->clk;

    case 4: /* KMIIR */

        return s->pending | 2;

    default:

        hw_error("pl050_read: Bad offset %x\n", (int)offset);

        return 0;

    }

}

```

## H2R-008

### Query

```c

void ff_vp3_v_loop_filter_c(uint8_t *first_pixel, int stride, int *bounding_values)

{

    unsigned char *end;

    int filter_value;

    const int nstride= -stride;



    for (end= first_pixel + 8; first_pixel < end; first_pixel++) {

        filter_value =

            (first_pixel[2 * nstride] - first_pixel[ stride])

         +3*(first_pixel[0          ] - first_pixel[nstride]);

        filter_value = bounding_values[(filter_value + 4) >> 3];

        first_pixel[nstride] = av_clip_uint8(first_pixel[nstride] + filter_value);

        first_pixel[0] = av_clip_uint8(first_pixel[0] - filter_value);

    }

}

```

### Demonstration

```c

static void horizontal_filter(unsigned char *first_pixel, int stride,

    int *bounding_values)

{

    unsigned char *end;

    int filter_value;



    for (end= first_pixel + 8*stride; first_pixel < end; first_pixel += stride) {

        filter_value =

            (first_pixel[-2] - first_pixel[ 1])

         +3*(first_pixel[ 0] - first_pixel[-1]);

        filter_value = bounding_values[(filter_value + 4) >> 3];

        first_pixel[-1] = clip_uint8(first_pixel[-1] + filter_value);

        first_pixel[ 0] = clip_uint8(first_pixel[ 0] - filter_value);

    }

}

```

## H2R-009

### Query

```c

static bool bdrv_drain_recurse(BlockDriverState *bs, bool begin)

{

    BdrvChild *child, *tmp;

    bool waited;



    /* Ensure any pending metadata writes are submitted to bs->file.  */

    bdrv_drain_invoke(bs, begin);



    /* Wait for drained requests to finish */

    waited = BDRV_POLL_WHILE(bs, atomic_read(&bs->in_flight) > 0);



    QLIST_FOREACH_SAFE(child, &bs->children, next, tmp) {

        BlockDriverState *bs = child->bs;

        bool in_main_loop =

            qemu_get_current_aio_context() == qemu_get_aio_context();

        assert(bs->refcnt > 0);

        if (in_main_loop) {

            /* In case the recursive bdrv_drain_recurse processes a

             * block_job_defer_to_main_loop BH and modifies the graph,

             * let's hold a reference to bs until we are done.

             *

             * IOThread doesn't have such a BH, and it is not safe to call

             * bdrv_unref without BQL, so skip doing it there.

             */

            bdrv_ref(bs);

        }

        waited |= bdrv_drain_recurse(bs, begin);

        if (in_main_loop) {

            bdrv_unref(bs);

        }

    }



    return waited;

}

```

### Demonstration

```c

static void coroutine_fn wait_for_overlapping_requests(BlockDriverState *bs,

        BdrvTrackedRequest *self, int64_t offset, unsigned int bytes)

{

    BdrvTrackedRequest *req;

    int64_t cluster_offset;

    unsigned int cluster_bytes;

    bool retry;



    /* If we touch the same cluster it counts as an overlap.  This guarantees

     * that allocating writes will be serialized and not race with each other

     * for the same cluster.  For example, in copy-on-read it ensures that the

     * CoR read and write operations are atomic and guest writes cannot

     * interleave between them.

     */

    round_bytes_to_clusters(bs, offset, bytes, &cluster_offset, &cluster_bytes);



    do {

        retry = false;

        QLIST_FOREACH(req, &bs->tracked_requests, list) {

            if (req == self) {

                continue;

            }

            if (tracked_request_overlaps(req, cluster_offset, cluster_bytes)) {

                /* Hitting this means there was a reentrant request, for

                 * example, a block driver issuing nested requests.  This must

                 * never happen since it means deadlock.

                 */

                assert(qemu_coroutine_self() != req->co);



                qemu_co_queue_wait(&req->wait_queue);

                retry = true;

                break;

            }

        }

    } while (retry);

}

```

## H2R-010

### Query

```c

static int msrle_decode_8_16_24_32(AVCodecContext *avctx, AVPicture *pic, int depth,

                                    const uint8_t *data, int srcsize)

{

    uint8_t *output, *output_end;

    const uint8_t* src = data;

    int p1, p2, line=avctx->height, pos=0, i;

    uint16_t pix16;

    uint32_t pix32;



    output = pic->data[0] + (avctx->height - 1) * pic->linesize[0];

    output_end = pic->data[0] + (avctx->height) * pic->linesize[0];

    while(src < data + srcsize) {

        p1 = *src++;

        if(p1 == 0) { //Escape code

            p2 = *src++;

            if(p2 == 0) { //End-of-line

                output = pic->data[0] + (--line) * pic->linesize[0];

                if (line < 0){

                    av_log(avctx, AV_LOG_ERROR, "Next line is beyond picture bounds\n");

                    return -1;

                }

                pos = 0;

                continue;

            } else if(p2 == 1) { //End-of-picture

                return 0;

            } else if(p2 == 2) { //Skip

                p1 = *src++;

                p2 = *src++;

                line -= p2;

                if (line < 0){

                    av_log(avctx, AV_LOG_ERROR, "Skip beyond picture bounds\n");

                    return -1;

                }

                pos += p1;

                output = pic->data[0] + line * pic->linesize[0] + pos * (depth >> 3);

                continue;

            }

            // Copy data

            if (output + p2 * (depth >> 3) > output_end) {

                src += p2 * (depth >> 3);

                continue;

            }

            if ((depth == 8) || (depth == 24)) {

                for(i = 0; i < p2 * (depth >> 3); i++) {

                    *output++ = *src++;

                }

                // RLE8 copy is actually padded - and runs are not!

                if(depth == 8 && (p2 & 1)) {

                    src++;

                }

            } else if (depth == 16) {

                for(i = 0; i < p2; i++) {

                    pix16 = AV_RL16(src);

                    src += 2;

                    *(uint16_t*)output = pix16;

                    output += 2;

                }

            } else if (depth == 32) {

                for(i = 0; i < p2; i++) {

                    pix32 = AV_RL32(src);

                    src += 4;

                    *(uint32_t*)output = pix32;

                    output += 4;

                }

            }

            pos += p2;

        } else { //Run of pixels

            uint8_t pix[3]; //original pixel

            switch(depth){

            case  8: pix[0] = *src++;

                     break;

            case 16: pix16 = AV_RL16(src);

                     src += 2;

                     break;

            case 24: pix[0] = *src++;

                     pix[1] = *src++;

                     pix[2] = *src++;

                     break;

            case 32: pix32 = AV_RL32(src);

                     src += 4;

                     break;

            }

            if (output + p1 * (depth >> 3) > output_end)

                continue;

            for(i = 0; i < p1; i++) {

                switch(depth){

                case  8: *output++ = pix[0];

                         break;

                case 16: *(uint16_t*)output = pix16;

                         output += 2;

                         break;

                case 24: *output++ = pix[0];

                         *output++ = pix[1];

                         *output++ = pix[2];

                         break;

                case 32: *(uint32_t*)output = pix32;

                         output += 4;

                         break;

                }

            }

            pos += p1;

        }

    }



    av_log(avctx, AV_LOG_WARNING, "MS RLE warning: no End-of-picture code\n");

    return 0;

}

```

### Demonstration

```c

static int msrle_decode_8_16_24_32(AVCodecContext *avctx, AVPicture *pic,

                                   int depth, GetByteContext *gb)

{

    uint8_t *output, *output_end;

    int p1, p2, line=avctx->height - 1, pos=0, i;

    uint16_t pix16;

    uint32_t pix32;

    unsigned int width= FFABS(pic->linesize[0]) / (depth >> 3);



    output     = pic->data[0] + (avctx->height - 1) * pic->linesize[0];

    output_end = pic->data[0] +  avctx->height      * pic->linesize[0];

    while (bytestream2_get_bytes_left(gb) > 0) {

        p1 = bytestream2_get_byteu(gb);

        if(p1 == 0) { //Escape code

            p2 = bytestream2_get_byte(gb);

            if(p2 == 0) { //End-of-line

                output = pic->data[0] + (--line) * pic->linesize[0];

                if (line < 0) {

                    if (bytestream2_get_be16(gb) == 1) { // end-of-picture

                        return 0;

                    } else {

                        av_log(avctx, AV_LOG_ERROR,

                               "Next line is beyond picture bounds (%d bytes left)\n",

                               bytestream2_get_bytes_left(gb));

                        return AVERROR_INVALIDDATA;

                    }

                }

                pos = 0;

                continue;

            } else if(p2 == 1) { //End-of-picture

                return 0;

            } else if(p2 == 2) { //Skip

                p1 = bytestream2_get_byte(gb);

                p2 = bytestream2_get_byte(gb);

                line -= p2;

                pos += p1;

                if (line < 0 || pos >= width){

                    av_log(avctx, AV_LOG_ERROR, "Skip beyond picture bounds\n");

                    return -1;

                }

                output = pic->data[0] + line * pic->linesize[0] + pos * (depth >> 3);

                continue;

            }

            // Copy data

            if ((pic->linesize[0] > 0 && output + p2 * (depth >> 3) > output_end) ||

                (pic->linesize[0] < 0 && output + p2 * (depth >> 3) < output_end)) {

                bytestream2_skip(gb, 2 * (depth >> 3));

                continue;

            } else if (bytestream2_get_bytes_left(gb) < p2 * (depth >> 3)) {

                av_log(avctx, AV_LOG_ERROR, "bytestream overrun\n");

                return AVERROR_INVALIDDATA;

            }



            if ((depth == 8) || (depth == 24)) {

                for(i = 0; i < p2 * (depth >> 3); i++) {

                    *output++ = bytestream2_get_byteu(gb);

                }

                // RLE8 copy is actually padded - and runs are not!

                if(depth == 8 && (p2 & 1)) {

                    bytestream2_skip(gb, 1);

                }

            } else if (depth == 16) {

                for(i = 0; i < p2; i++) {

                    *(uint16_t*)output = bytestream2_get_le16u(gb);

                    output += 2;

                }

            } else if (depth == 32) {

                for(i = 0; i < p2; i++) {

                    *(uint32_t*)output = bytestream2_get_le32u(gb);

                    output += 4;

                }

            }

            pos += p2;

        } else { //run of pixels

            uint8_t pix[3]; //original pixel

            if ((pic->linesize[0] > 0 && output + p1 * (depth >> 3) > output_end) ||

                (pic->linesize[0] < 0 && output + p1 * (depth >> 3) < output_end))

                continue;

            switch(depth){

            case  8: pix[0] = bytestream2_get_byte(gb);

                     break;

            case 16: pix16  = bytestream2_get_le16(gb);

                     break;

            case 24: pix[0] = bytestream2_get_byte(gb);

                     pix[1] = bytestream2_get_byte(gb);

                     pix[2] = bytestream2_get_byte(gb);

                     break;

            case 32: pix32  = bytestream2_get_le32(gb);

                     break;

            }

            switch(depth){

            case  8:

                for(i = 0; i < p1; i++)

                        *output++ = pix[0];

                break;

            case 16:

                for(i = 0; i < p1; i++) {

                        *(uint16_t*)output = pix16;

                        output += 2;

                }

                break;

            case 24:

                for(i = 0; i < p1; i++) {

                        *output++ = pix[0];

                        *output++ = pix[1];

                        *output++ = pix[2];

                }

                break;

            case 32:

                for(i = 0; i < p1; i++) {

                        *(uint32_t*)output = pix32;

                        output += 4;

                }

                break;

            }

            pos += p1;

        }

    }



    av_log(avctx, AV_LOG_WARNING, "MS RLE warning: no end-of-picture code\n");

    return 0;

}

```

## H2R-011

### Query

```c

DISAS_INSN(divw)

{

    TCGv reg;

    TCGv tmp;

    TCGv src;

    int sign;



    sign = (insn & 0x100) != 0;

    reg = DREG(insn, 9);

    if (sign) {

        tcg_gen_ext16s_i32(QREG_DIV1, reg);

    } else {

        tcg_gen_ext16u_i32(QREG_DIV1, reg);

    }

    SRC_EA(env, src, OS_WORD, sign, NULL);

    tcg_gen_mov_i32(QREG_DIV2, src);

    if (sign) {

        gen_helper_divs(cpu_env, tcg_const_i32(1));

    } else {

        gen_helper_divu(cpu_env, tcg_const_i32(1));

    }



    tmp = tcg_temp_new();

    src = tcg_temp_new();

    tcg_gen_ext16u_i32(tmp, QREG_DIV1);

    tcg_gen_shli_i32(src, QREG_DIV2, 16);

    tcg_gen_or_i32(reg, tmp, src);



    set_cc_op(s, CC_OP_FLAGS);

}

```

### Demonstration

```c

DISAS_INSN(shift_im)

{

    TCGv reg;

    int tmp;

    TCGv shift;



    set_cc_op(s, CC_OP_FLAGS);



    reg = DREG(insn, 0);

    tmp = (insn >> 9) & 7;

    if (tmp == 0)

        tmp = 8;

    shift = tcg_const_i32(tmp);

    /* No need to flush flags becuse we know we will set C flag.  */

    if (insn & 0x100) {

        gen_helper_shl_cc(reg, cpu_env, reg, shift);

    } else {

        if (insn & 8) {

            gen_helper_shr_cc(reg, cpu_env, reg, shift);

        } else {

            gen_helper_sar_cc(reg, cpu_env, reg, shift);

        }

    }

}

```

## H2R-012

### Query

```c

static int fourxm_read_packet(AVFormatContext *s,

                              AVPacket *pkt)

{

    FourxmDemuxContext *fourxm = s->priv_data;

    ByteIOContext *pb = &s->pb;

    unsigned int fourcc_tag;

    unsigned int size, out_size;

    int ret = 0;

    int track_number;

    int packet_read = 0;

    unsigned char header[8];

    int64_t pts_inc;

    int audio_frame_count;



    while (!packet_read) {



        if ((ret = get_buffer(&s->pb, header, 8)) < 0)

            return ret;

        fourcc_tag = LE_32(&header[0]);

        size = LE_32(&header[4]);

        if (url_feof(pb))

            return AVERROR_IO;

        switch (fourcc_tag) {



        case LIST_TAG:

            /* this is a good time to bump the video pts */

            fourxm->video_pts += fourxm->video_pts_inc;



            /* skip the LIST-* tag and move on to the next fourcc */

            get_le32(pb);

            break;



        case ifrm_TAG:

        case pfrm_TAG:

        case cfrm_TAG:{



            /* allocate 8 more bytes than 'size' to account for fourcc

             * and size */

            if (av_new_packet(pkt, size + 8))

                return AVERROR_IO;

            pkt->stream_index = fourxm->video_stream_index;

            pkt->pts = fourxm->video_pts;

            memcpy(pkt->data, header, 8);

            ret = get_buffer(&s->pb, &pkt->data[8], size);



            if (ret < 0)

                av_free_packet(pkt);

            else

                packet_read = 1;

            break;

        }



        case snd__TAG:

            track_number = get_le32(pb);

            out_size= get_le32(pb);

            size-=8;



            if (track_number == fourxm->selected_track) {

                if (av_new_packet(pkt, size))

                    return AVERROR_IO;

                pkt->stream_index = 

                    fourxm->tracks[fourxm->selected_track].stream_index;

                pkt->pts = fourxm->audio_pts;

                ret = get_buffer(&s->pb, pkt->data, size);

                if (ret < 0)

                    av_free_packet(pkt);

                else

                    packet_read = 1;



                /* pts accounting */

                audio_frame_count = size;

                if (fourxm->tracks[fourxm->selected_track].adpcm)

                    audio_frame_count -= 

                        2 * (fourxm->tracks[fourxm->selected_track].channels);

                audio_frame_count /=

                      fourxm->tracks[fourxm->selected_track].channels;

                if (fourxm->tracks[fourxm->selected_track].adpcm)

                    audio_frame_count *= 2;

                else 

                    audio_frame_count /=

                    (fourxm->tracks[fourxm->selected_track].bits / 8);

                pts_inc = audio_frame_count;

                pts_inc *= 90000;

                pts_inc /= fourxm->tracks[fourxm->selected_track].sample_rate;

                fourxm->audio_pts += pts_inc;



            } else {

                url_fseek(pb, size, SEEK_CUR);

            }

            break;



        default:

            url_fseek(pb, size, SEEK_CUR);

            break;

        }

    }

    return ret;

}

```

### Demonstration

```c

static int fourxm_read_packet(AVFormatContext *s,

                              AVPacket *pkt)

{

    FourxmDemuxContext *fourxm = s->priv_data;

    ByteIOContext *pb = s->pb;

    unsigned int fourcc_tag;

    unsigned int size, out_size;

    int ret = 0;

    unsigned int track_number;

    int packet_read = 0;

    unsigned char header[8];

    int audio_frame_count;



    while (!packet_read) {



        if ((ret = get_buffer(s->pb, header, 8)) < 0)

            return ret;

        fourcc_tag = AV_RL32(&header[0]);

        size = AV_RL32(&header[4]);

        if (url_feof(pb))

            return AVERROR(EIO);

        switch (fourcc_tag) {



        case LIST_TAG:

            /* this is a good time to bump the video pts */

            fourxm->video_pts ++;



            /* skip the LIST-* tag and move on to the next fourcc */

            get_le32(pb);

            break;



        case ifrm_TAG:

        case pfrm_TAG:

        case cfrm_TAG:

        case ifr2_TAG:

        case pfr2_TAG:

        case cfr2_TAG:

            /* allocate 8 more bytes than 'size' to account for fourcc

             * and size */

            if (size + 8 < size || av_new_packet(pkt, size + 8))

                return AVERROR(EIO);

            pkt->stream_index = fourxm->video_stream_index;

            pkt->pts = fourxm->video_pts;

            pkt->pos = url_ftell(s->pb);

            memcpy(pkt->data, header, 8);

            ret = get_buffer(s->pb, &pkt->data[8], size);



            if (ret < 0){

                av_free_packet(pkt);

            }else

                packet_read = 1;

            break;



        case snd__TAG:

            track_number = get_le32(pb);

            out_size= get_le32(pb);

            size-=8;



            if (track_number < fourxm->track_count) {

                ret= av_get_packet(s->pb, pkt, size);

                if(ret<0)

                    return AVERROR(EIO);

                pkt->stream_index =

                    fourxm->tracks[track_number].stream_index;

                pkt->pts = fourxm->tracks[track_number].audio_pts;

                packet_read = 1;



                /* pts accounting */

                audio_frame_count = size;

                if (fourxm->tracks[track_number].adpcm)

                    audio_frame_count -=

                        2 * (fourxm->tracks[track_number].channels);

                audio_frame_count /=

                      fourxm->tracks[track_number].channels;

                if (fourxm->tracks[track_number].adpcm){

                    audio_frame_count *= 2;

                }else

                    audio_frame_count /=

                    (fourxm->tracks[track_number].bits / 8);

                fourxm->tracks[track_number].audio_pts += audio_frame_count;



            } else {

                url_fseek(pb, size, SEEK_CUR);

            }

            break;



        default:

            url_fseek(pb, size, SEEK_CUR);

            break;

        }

    }

    return ret;

}

```

## H2R-013

### Query

```c

static void backup_duplicate_context(MpegEncContext *bak, MpegEncContext *src){

#define COPY(a) bak->a= src->a

    COPY(allocated_edge_emu_buffer);

    COPY(edge_emu_buffer);

    COPY(me.scratchpad);

    COPY(me.temp);

    COPY(rd_scratchpad);

    COPY(b_scratchpad);

    COPY(obmc_scratchpad);

    COPY(me.map);

    COPY(me.score_map);

    COPY(blocks);

    COPY(block);

    COPY(start_mb_y);

    COPY(end_mb_y);

    COPY(me.map_generation);

    COPY(pb);

    COPY(dct_error_sum);

    COPY(dct_count[0]);

    COPY(dct_count[1]);

    COPY(ac_val_base);

    COPY(ac_val[0]);

    COPY(ac_val[1]);

    COPY(ac_val[2]);

#undef COPY

}

```

### Demonstration

```c

static void tmu2_write(void *opaque, target_phys_addr_t addr, uint64_t value,

                       unsigned size)

{

    MilkymistTMU2State *s = opaque;



    trace_milkymist_tmu2_memory_write(addr, value);



    addr >>= 2;

    switch (addr) {

    case R_CTL:

        s->regs[addr] = value;

        if (value & CTL_START_BUSY) {

            tmu2_start(s);

        }

        break;

    case R_BRIGHTNESS:

    case R_HMESHLAST:

    case R_VMESHLAST:

    case R_CHROMAKEY:

    case R_VERTICESADDR:

    case R_TEXFBUF:

    case R_TEXHRES:

    case R_TEXVRES:

    case R_TEXHMASK:

    case R_TEXVMASK:

    case R_DSTFBUF:

    case R_DSTHRES:

    case R_DSTVRES:

    case R_DSTHOFFSET:

    case R_DSTVOFFSET:

    case R_DSTSQUAREW:

    case R_DSTSQUAREH:

    case R_ALPHA:

        s->regs[addr] = value;

        break;



    default:

        error_report("milkymist_tmu2: write access to unknown register 0x"

                TARGET_FMT_plx, addr << 2);

        break;

    }



    tmu2_check_registers(s);

}

```

## H2R-014

### Query

```c

void ide_sector_read(IDEState *s)

{

    int64_t sector_num;

    int ret, n;



    s->status = READY_STAT | SEEK_STAT;

    s->error = 0; /* not needed by IDE spec, but needed by Windows */

    sector_num = ide_get_sector(s);

    n = s->nsector;

    if (n == 0) {

        /* no more sector to read from disk */

        ide_transfer_stop(s);

    } else {

#if defined(DEBUG_IDE)

        printf("read sector=%" PRId64 "\n", sector_num);

#endif

        if (n > s->req_nb_sectors)

            n = s->req_nb_sectors;



        bdrv_acct_start(s->bs, &s->acct, n * BDRV_SECTOR_SIZE, BDRV_ACCT_READ);

        ret = bdrv_read(s->bs, sector_num, s->io_buffer, n);

        bdrv_acct_done(s->bs, &s->acct);

        if (ret != 0) {

            if (ide_handle_rw_error(s, -ret,

                BM_STATUS_PIO_RETRY | BM_STATUS_RETRY_READ))

            {

                return;

            }

        }

        ide_transfer_start(s, s->io_buffer, 512 * n, ide_sector_read);

        ide_set_irq(s->bus);

        ide_set_sector(s, sector_num + n);

        s->nsector -= n;

    }

}

```

### Demonstration

```c

static int copy_sectors(BlockDriverState *bs, uint64_t start_sect,

                        uint64_t cluster_offset, int n_start, int n_end)

{

    BDRVQcowState *s = bs->opaque;

    int n, ret;

    void *buf;



    /*

     * If this is the last cluster and it is only partially used, we must only

     * copy until the end of the image, or bdrv_check_request will fail for the

     * bdrv_read/write calls below.

     */

    if (start_sect + n_end > bs->total_sectors) {

        n_end = bs->total_sectors - start_sect;

    }



    n = n_end - n_start;

    if (n <= 0) {

        return 0;

    }



    buf = qemu_blockalign(bs, n * BDRV_SECTOR_SIZE);



    BLKDBG_EVENT(bs->file, BLKDBG_COW_READ);

    ret = bdrv_read(bs, start_sect + n_start, buf, n);

    if (ret < 0) {

        goto out;

    }



    if (s->crypt_method) {

        qcow2_encrypt_sectors(s, start_sect + n_start,

                        buf, buf, n, 1,

                        &s->aes_encrypt_key);

    }



    BLKDBG_EVENT(bs->file, BLKDBG_COW_WRITE);

    ret = bdrv_write(bs->file, (cluster_offset >> 9) + n_start, buf, n);

    if (ret < 0) {

        goto out;

    }



    ret = 0;

out:

    qemu_vfree(buf);

    return ret;

}

```

## H2R-015

### Query

```c

static void openpic_load_IRQ_queue(QEMUFile* f, IRQQueue *q)

{

    unsigned int i;



    for (i = 0; i < BF_WIDTH(MAX_IRQ); i++)

        qemu_get_be32s(f, &q->queue[i]);



    qemu_get_sbe32s(f, &q->next);

    qemu_get_sbe32s(f, &q->priority);

}

```

### Demonstration

```c

static void openpic_load_IRQ_queue(QEMUFile* f, IRQ_queue_t *q)

{

    unsigned int i;



    for (i = 0; i < BF_WIDTH(MAX_IRQ); i++)

        qemu_get_be32s(f, &q->queue[i]);



    qemu_get_sbe32s(f, &q->next);

    qemu_get_sbe32s(f, &q->priority);

}

```

## H2R-016

### Query

```c

static av_cold OMXContext *omx_init(void *logctx, const char *libname, const char *prefix)

{

    static const char * const libnames[] = {

        "libOMX_Core.so",

        "libOmxCore.so",

        NULL

    };

    const char* const* nameptr;

    int ret = AVERROR_ENCODER_NOT_FOUND;

    OMXContext *omx_context;



    omx_context = av_mallocz(sizeof(*omx_context));

    if (!omx_context)

        return NULL;

    if (libname) {

        ret = omx_try_load(omx_context, logctx, libname, prefix);

        if (ret < 0) {

            av_free(omx_context);

            return NULL;

        }

    } else {

        for (nameptr = libnames; *nameptr; nameptr++)

            if (!(ret = omx_try_load(omx_context, logctx, *nameptr, prefix)))

                break;

        if (!*nameptr) {

            av_free(omx_context);

            return NULL;

        }

    }



    omx_context->ptr_Init();

    return omx_context;

}

```

### Demonstration

```c

static av_cold int find_component(OMXContext *omx_context, void *logctx,

                                  const char *role, char *str, int str_size)

{

    OMX_U32 i, num = 0;

    char **components;

    int ret = 0;



#if CONFIG_OMX_RPI

    if (av_strstart(role, "video_encoder.", NULL)) {

        av_strlcpy(str, "OMX.broadcom.video_encode", str_size);

        return 0;

    }

#endif

    omx_context->ptr_GetComponentsOfRole((OMX_STRING) role, &num, NULL);

    if (!num) {

        av_log(logctx, AV_LOG_WARNING, "No component for role %s found\n", role);

        return AVERROR_ENCODER_NOT_FOUND;

    }

    components = av_mallocz(sizeof(char*) * num);

    if (!components)

        return AVERROR(ENOMEM);

    for (i = 0; i < num; i++) {

        components[i] = av_mallocz(OMX_MAX_STRINGNAME_SIZE);

        if (!components) {

            ret = AVERROR(ENOMEM);

            goto end;

        }

    }

    omx_context->ptr_GetComponentsOfRole((OMX_STRING) role, &num, (OMX_U8**) components);

    av_strlcpy(str, components[0], str_size);

end:

    for (i = 0; i < num; i++)

        av_free(components[i]);

    av_free(components);

    return ret;

}

```

## H2R-017

### Query

```c

static void generate_offset_lut(DiracGolombLUT *lut, int off)

{

    int idx;

    for (idx = 0; idx < LUT_SIZE; idx++) {

        DiracGolombLUT *l = &lut[idx];



        INIT_RESIDUE(res);

        SET_RESIDUE(res, idx, LUT_BITS);



        l->preamble      = CONVERT_TO_RESIDUE(res >> (RSIZE_BITS - off), off);

        l->preamble_bits = off;

        l->sign = ((l->preamble >> (RSIZE_BITS - l->preamble_bits)) & 1) ? -1 : +1;



        search_for_golomb(l, res << off, LUT_BITS - off);

    }

}

```

### Demonstration

```c

static uint64_t ich_elrsr_read(CPUARMState *env, const ARMCPRegInfo *ri)

{

    GICv3CPUState *cs = icc_cs_from_env(env);

    uint64_t value = 0;

    int i;



    for (i = 0; i < cs->num_list_regs; i++) {

        uint64_t lr = cs->ich_lr_el2[i];



        if ((lr & ICH_LR_EL2_STATE_MASK) == 0 &&

            ((lr & ICH_LR_EL2_HW) == 1 || (lr & ICH_LR_EL2_EOI) == 0)) {

            value |= (1 << i);

        }

    }



    trace_gicv3_ich_elrsr_read(gicv3_redist_affid(cs), value);

    return value;

}

```

## H2R-018

### Query

```c

static int iscsi_open(BlockDriverState *bs, const char *filename, int flags)

{

    IscsiLun *iscsilun = bs->opaque;

    struct iscsi_context *iscsi = NULL;

    struct iscsi_url *iscsi_url = NULL;

    struct IscsiTask task;

    char *initiator_name = NULL;

    int ret;



    if ((BDRV_SECTOR_SIZE % 512) != 0) {

        error_report("iSCSI: Invalid BDRV_SECTOR_SIZE. "

                     "BDRV_SECTOR_SIZE(%lld) is not a multiple "

                     "of 512", BDRV_SECTOR_SIZE);

        return -EINVAL;

    }



    iscsi_url = iscsi_parse_full_url(iscsi, filename);

    if (iscsi_url == NULL) {

        error_report("Failed to parse URL : %s %s", filename,

                     iscsi_get_error(iscsi));

        ret = -EINVAL;

        goto out;

    }



    memset(iscsilun, 0, sizeof(IscsiLun));



    initiator_name = parse_initiator_name(iscsi_url->target);



    iscsi = iscsi_create_context(initiator_name);

    if (iscsi == NULL) {

        error_report("iSCSI: Failed to create iSCSI context.");

        ret = -ENOMEM;

        goto out;

    }



    if (iscsi_set_targetname(iscsi, iscsi_url->target)) {

        error_report("iSCSI: Failed to set target name.");

        ret = -EINVAL;

        goto out;

    }



    if (iscsi_url->user != NULL) {

        ret = iscsi_set_initiator_username_pwd(iscsi, iscsi_url->user,

                                              iscsi_url->passwd);

        if (ret != 0) {

            error_report("Failed to set initiator username and password");

            ret = -EINVAL;

            goto out;

        }

    }



    /* check if we got CHAP username/password via the options */

    if (parse_chap(iscsi, iscsi_url->target) != 0) {

        error_report("iSCSI: Failed to set CHAP user/password");

        ret = -EINVAL;

        goto out;

    }



    if (iscsi_set_session_type(iscsi, ISCSI_SESSION_NORMAL) != 0) {

        error_report("iSCSI: Failed to set session type to normal.");

        ret = -EINVAL;

        goto out;

    }



    iscsi_set_header_digest(iscsi, ISCSI_HEADER_DIGEST_NONE_CRC32C);



    /* check if we got HEADER_DIGEST via the options */

    parse_header_digest(iscsi, iscsi_url->target);



    task.iscsilun = iscsilun;

    task.status = 0;

    task.complete = 0;

    task.bs = bs;



    iscsilun->iscsi = iscsi;

    iscsilun->lun   = iscsi_url->lun;



    if (iscsi_full_connect_async(iscsi, iscsi_url->portal, iscsi_url->lun,

                                 iscsi_connect_cb, &task)

        != 0) {

        error_report("iSCSI: Failed to start async connect.");

        ret = -EINVAL;

        goto out;

    }



    while (!task.complete) {

        iscsi_set_events(iscsilun);

        qemu_aio_wait();

    }

    if (task.status != 0) {

        error_report("iSCSI: Failed to connect to LUN : %s",

                     iscsi_get_error(iscsi));

        ret = -EINVAL;

        goto out;

    }



    /* Medium changer or tape. We dont have any emulation for this so this must

     * be sg ioctl compatible. We force it to be sg, otherwise qemu will try

     * to read from the device to guess the image format.

     */

    if (iscsilun->type == TYPE_MEDIUM_CHANGER ||

        iscsilun->type == TYPE_TAPE) {

        bs->sg = 1;

    }



    ret = 0;



out:

    if (initiator_name != NULL) {

        g_free(initiator_name);

    }

    if (iscsi_url != NULL) {

        iscsi_destroy_url(iscsi_url);

    }



    if (ret) {

        if (iscsi != NULL) {

            iscsi_destroy_context(iscsi);

        }

        memset(iscsilun, 0, sizeof(IscsiLun));

    }

    return ret;

}

```

### Demonstration

```c

static int iscsi_open(BlockDriverState *bs, QDict *options, int flags,

                      Error **errp)

{

    IscsiLun *iscsilun = bs->opaque;

    struct iscsi_context *iscsi = NULL;

    struct iscsi_url *iscsi_url = NULL;

    struct scsi_task *task = NULL;

    struct scsi_inquiry_standard *inq = NULL;

    struct scsi_inquiry_supported_pages *inq_vpd;

    char *initiator_name = NULL;

    QemuOpts *opts;

    Error *local_err = NULL;

    const char *filename;

    int i, ret;



    if ((BDRV_SECTOR_SIZE % 512) != 0) {

        error_setg(errp, "iSCSI: Invalid BDRV_SECTOR_SIZE. "

                   "BDRV_SECTOR_SIZE(%lld) is not a multiple "

                   "of 512", BDRV_SECTOR_SIZE);

        return -EINVAL;

    }



    opts = qemu_opts_create(&runtime_opts, NULL, 0, &error_abort);

    qemu_opts_absorb_qdict(opts, options, &local_err);

    if (local_err) {

        error_propagate(errp, local_err);

        ret = -EINVAL;

        goto out;

    }



    filename = qemu_opt_get(opts, "filename");



    iscsi_url = iscsi_parse_full_url(iscsi, filename);

    if (iscsi_url == NULL) {

        error_setg(errp, "Failed to parse URL : %s", filename);

        ret = -EINVAL;

        goto out;

    }



    memset(iscsilun, 0, sizeof(IscsiLun));



    initiator_name = parse_initiator_name(iscsi_url->target);



    iscsi = iscsi_create_context(initiator_name);

    if (iscsi == NULL) {

        error_setg(errp, "iSCSI: Failed to create iSCSI context.");

        ret = -ENOMEM;

        goto out;

    }



    if (iscsi_set_targetname(iscsi, iscsi_url->target)) {

        error_setg(errp, "iSCSI: Failed to set target name.");

        ret = -EINVAL;

        goto out;

    }



    if (iscsi_url->user != NULL) {

        ret = iscsi_set_initiator_username_pwd(iscsi, iscsi_url->user,

                                              iscsi_url->passwd);

        if (ret != 0) {

            error_setg(errp, "Failed to set initiator username and password");

            ret = -EINVAL;

            goto out;

        }

    }



    /* check if we got CHAP username/password via the options */

    parse_chap(iscsi, iscsi_url->target, &local_err);

    if (local_err != NULL) {

        error_propagate(errp, local_err);

        ret = -EINVAL;

        goto out;

    }



    if (iscsi_set_session_type(iscsi, ISCSI_SESSION_NORMAL) != 0) {

        error_setg(errp, "iSCSI: Failed to set session type to normal.");

        ret = -EINVAL;

        goto out;

    }



    iscsi_set_header_digest(iscsi, ISCSI_HEADER_DIGEST_NONE_CRC32C);



    /* check if we got HEADER_DIGEST via the options */

    parse_header_digest(iscsi, iscsi_url->target, &local_err);

    if (local_err != NULL) {

        error_propagate(errp, local_err);

        ret = -EINVAL;

        goto out;

    }



    if (iscsi_full_connect_sync(iscsi, iscsi_url->portal, iscsi_url->lun) != 0) {

        error_setg(errp, "iSCSI: Failed to connect to LUN : %s",

            iscsi_get_error(iscsi));

        ret = -EINVAL;

        goto out;

    }



    iscsilun->iscsi = iscsi;

    iscsilun->aio_context = bdrv_get_aio_context(bs);

    iscsilun->lun   = iscsi_url->lun;

    iscsilun->has_write_same = true;



    task = iscsi_do_inquiry(iscsilun->iscsi, iscsilun->lun, 0, 0,

                            (void **) &inq, errp);

    if (task == NULL) {

        ret = -EINVAL;

        goto out;

    }

    iscsilun->type = inq->periperal_device_type;

    scsi_free_scsi_task(task);

    task = NULL;



    /* Check the write protect flag of the LUN if we want to write */

    if (iscsilun->type == TYPE_DISK && (flags & BDRV_O_RDWR) &&

        iscsi_is_write_protected(iscsilun)) {

        error_setg(errp, "Cannot open a write protected LUN as read-write");

        ret = -EACCES;

        goto out;

    }



    iscsi_readcapacity_sync(iscsilun, &local_err);

    if (local_err != NULL) {

        error_propagate(errp, local_err);

        ret = -EINVAL;

        goto out;

    }

    bs->total_sectors = sector_lun2qemu(iscsilun->num_blocks, iscsilun);

    bs->request_alignment = iscsilun->block_size;



    /* We don't have any emulation for devices other than disks and CD-ROMs, so

     * this must be sg ioctl compatible. We force it to be sg, otherwise qemu

     * will try to read from the device to guess the image format.

     */

    if (iscsilun->type != TYPE_DISK && iscsilun->type != TYPE_ROM) {

        bs->sg = 1;

    }



    task = iscsi_do_inquiry(iscsilun->iscsi, iscsilun->lun, 1,

                            SCSI_INQUIRY_PAGECODE_SUPPORTED_VPD_PAGES,

                            (void **) &inq_vpd, errp);

    if (task == NULL) {

        ret = -EINVAL;

        goto out;

    }

    for (i = 0; i < inq_vpd->num_pages; i++) {

        struct scsi_task *inq_task;

        struct scsi_inquiry_logical_block_provisioning *inq_lbp;

        struct scsi_inquiry_block_limits *inq_bl;

        switch (inq_vpd->pages[i]) {

        case SCSI_INQUIRY_PAGECODE_LOGICAL_BLOCK_PROVISIONING:

            inq_task = iscsi_do_inquiry(iscsilun->iscsi, iscsilun->lun, 1,

                                        SCSI_INQUIRY_PAGECODE_LOGICAL_BLOCK_PROVISIONING,

                                        (void **) &inq_lbp, errp);

            if (inq_task == NULL) {

                ret = -EINVAL;

                goto out;

            }

            memcpy(&iscsilun->lbp, inq_lbp,

                   sizeof(struct scsi_inquiry_logical_block_provisioning));

            scsi_free_scsi_task(inq_task);

            break;

        case SCSI_INQUIRY_PAGECODE_BLOCK_LIMITS:

            inq_task = iscsi_do_inquiry(iscsilun->iscsi, iscsilun->lun, 1,

                                    SCSI_INQUIRY_PAGECODE_BLOCK_LIMITS,

                                    (void **) &inq_bl, errp);

            if (inq_task == NULL) {

                ret = -EINVAL;

                goto out;

            }

            memcpy(&iscsilun->bl, inq_bl,

                   sizeof(struct scsi_inquiry_block_limits));

            scsi_free_scsi_task(inq_task);

            break;

        default:

            break;

        }

    }

    scsi_free_scsi_task(task);

    task = NULL;



    iscsi_attach_aio_context(bs, iscsilun->aio_context);



    /* Guess the internal cluster (page) size of the iscsi target by the means

     * of opt_unmap_gran. Transfer the unmap granularity only if it has a

     * reasonable size */

    if (iscsilun->bl.opt_unmap_gran * iscsilun->block_size >= 4 * 1024 &&

        iscsilun->bl.opt_unmap_gran * iscsilun->block_size <= 16 * 1024 * 1024) {

        iscsilun->cluster_sectors = (iscsilun->bl.opt_unmap_gran *

                                     iscsilun->block_size) >> BDRV_SECTOR_BITS;

        if (iscsilun->lbprz && !(bs->open_flags & BDRV_O_NOCACHE)) {

            iscsilun->allocationmap = iscsi_allocationmap_init(iscsilun);

            if (iscsilun->allocationmap == NULL) {

                ret = -ENOMEM;

            }

        }

    }



out:

    qemu_opts_del(opts);

    g_free(initiator_name);

    if (iscsi_url != NULL) {

        iscsi_destroy_url(iscsi_url);

    }

    if (task != NULL) {

        scsi_free_scsi_task(task);

    }



    if (ret) {

        if (iscsi != NULL) {

            iscsi_destroy_context(iscsi);

        }

        memset(iscsilun, 0, sizeof(IscsiLun));

    }

    return ret;

}

```

## H2R-019

### Query

```c

static int decode_slice(struct AVCodecContext *avctx, void *arg)

{

    H264Context *h = *(void **)arg;

    int lf_x_start = h->mb_x;



    h->mb_skip_run = -1;



    av_assert0(h->block_offset[15] == (4 * ((scan8[15] - scan8[0]) & 7) << h->pixel_shift) + 4 * h->linesize * ((scan8[15] - scan8[0]) >> 3));



    h->is_complex = FRAME_MBAFF(h) || h->picture_structure != PICT_FRAME ||

                    avctx->codec_id != AV_CODEC_ID_H264 ||

                    (CONFIG_GRAY && (h->flags & CODEC_FLAG_GRAY));



    if (!(h->avctx->active_thread_type & FF_THREAD_SLICE) && h->picture_structure == PICT_FRAME) {

        const int start_i  = av_clip(h->resync_mb_x + h->resync_mb_y * h->mb_width, 0, h->mb_num - 1);

        if (start_i) {

            int prev_status = h->er.error_status_table[h->er.mb_index2xy[start_i - 1]];

            prev_status &= ~ VP_START;

            if (prev_status != (ER_MV_END | ER_DC_END | ER_AC_END))

                h->er.error_occurred = 1;

        }

    }



    if (h->pps.cabac) {

        /* realign */

        align_get_bits(&h->gb);



        /* init cabac */

        ff_init_cabac_decoder(&h->cabac,

                              h->gb.buffer + get_bits_count(&h->gb) / 8,

                              (get_bits_left(&h->gb) + 7) / 8);



        ff_h264_init_cabac_states(h);



        for (;;) {

            // START_TIMER

            int ret = ff_h264_decode_mb_cabac(h);

            int eos;

            // STOP_TIMER("decode_mb_cabac")



            if (ret >= 0)

                ff_h264_hl_decode_mb(h);



            // FIXME optimal? or let mb_decode decode 16x32 ?

            if (ret >= 0 && FRAME_MBAFF(h)) {

                h->mb_y++;



                ret = ff_h264_decode_mb_cabac(h);



                if (ret >= 0)

                    ff_h264_hl_decode_mb(h);

                h->mb_y--;

            }

            eos = get_cabac_terminate(&h->cabac);



            if ((h->workaround_bugs & FF_BUG_TRUNCATED) &&

                h->cabac.bytestream > h->cabac.bytestream_end + 2) {

                er_add_slice(h, h->resync_mb_x, h->resync_mb_y, h->mb_x - 1,

                                h->mb_y, ER_MB_END);

                if (h->mb_x >= lf_x_start)

                    loop_filter(h, lf_x_start, h->mb_x + 1);

                return 0;

            }

            if (h->cabac.bytestream > h->cabac.bytestream_end + 2 )

                av_log(h->avctx, AV_LOG_DEBUG, "bytestream overread %td\n", h->cabac.bytestream_end - h->cabac.bytestream);

            if (ret < 0 || h->cabac.bytestream > h->cabac.bytestream_end + 4) {

                av_log(h->avctx, AV_LOG_ERROR,

                       "error while decoding MB %d %d, bytestream (%td)\n",

                       h->mb_x, h->mb_y,

                       h->cabac.bytestream_end - h->cabac.bytestream);

                er_add_slice(h, h->resync_mb_x, h->resync_mb_y, h->mb_x,

                                h->mb_y, ER_MB_ERROR);

                return -1;

            }



            if (++h->mb_x >= h->mb_width) {

                loop_filter(h, lf_x_start, h->mb_x);

                h->mb_x = lf_x_start = 0;

                decode_finish_row(h);

                ++h->mb_y;

                if (FIELD_OR_MBAFF_PICTURE(h)) {

                    ++h->mb_y;

                    if (FRAME_MBAFF(h) && h->mb_y < h->mb_height)

                        predict_field_decoding_flag(h);

                }

            }



            if (eos || h->mb_y >= h->mb_height) {

                tprintf(h->avctx, "slice end %d %d\n",

                        get_bits_count(&h->gb), h->gb.size_in_bits);

                er_add_slice(h, h->resync_mb_x, h->resync_mb_y, h->mb_x - 1,

                                h->mb_y, ER_MB_END);

                if (h->mb_x > lf_x_start)

                    loop_filter(h, lf_x_start, h->mb_x);

                return 0;

            }

        }

    } else {

        for (;;) {

            int ret = ff_h264_decode_mb_cavlc(h);



            if (ret >= 0)

                ff_h264_hl_decode_mb(h);



            // FIXME optimal? or let mb_decode decode 16x32 ?

            if (ret >= 0 && FRAME_MBAFF(h)) {

                h->mb_y++;

                ret = ff_h264_decode_mb_cavlc(h);



                if (ret >= 0)

                    ff_h264_hl_decode_mb(h);

                h->mb_y--;

            }



            if (ret < 0) {

                av_log(h->avctx, AV_LOG_ERROR,

                       "error while decoding MB %d %d\n", h->mb_x, h->mb_y);

                er_add_slice(h, h->resync_mb_x, h->resync_mb_y, h->mb_x,

                                h->mb_y, ER_MB_ERROR);

                return -1;

            }



            if (++h->mb_x >= h->mb_width) {

                loop_filter(h, lf_x_start, h->mb_x);

                h->mb_x = lf_x_start = 0;

                decode_finish_row(h);

                ++h->mb_y;

                if (FIELD_OR_MBAFF_PICTURE(h)) {

                    ++h->mb_y;

                    if (FRAME_MBAFF(h) && h->mb_y < h->mb_height)

                        predict_field_decoding_flag(h);

                }

                if (h->mb_y >= h->mb_height) {

                    tprintf(h->avctx, "slice end %d %d\n",

                            get_bits_count(&h->gb), h->gb.size_in_bits);



                    if (   get_bits_left(&h->gb) == 0

                        || get_bits_left(&h->gb) > 0 && !(h->avctx->err_recognition & AV_EF_AGGRESSIVE)) {

                        er_add_slice(h, h->resync_mb_x, h->resync_mb_y,

                                        h->mb_x - 1, h->mb_y,

                                        ER_MB_END);



                        return 0;

                    } else {

                        er_add_slice(h, h->resync_mb_x, h->resync_mb_y,

                                        h->mb_x, h->mb_y,

                                        ER_MB_END);



                        return -1;

                    }

                }

            }



            if (get_bits_left(&h->gb) <= 0 && h->mb_skip_run <= 0) {

                tprintf(h->avctx, "slice end %d %d\n",

                        get_bits_count(&h->gb), h->gb.size_in_bits);

                if (get_bits_left(&h->gb) == 0) {

                    er_add_slice(h, h->resync_mb_x, h->resync_mb_y,

                                    h->mb_x - 1, h->mb_y,

                                    ER_MB_END);

                    if (h->mb_x > lf_x_start)

                        loop_filter(h, lf_x_start, h->mb_x);



                    return 0;

                } else {

                    er_add_slice(h, h->resync_mb_x, h->resync_mb_y, h->mb_x,

                                    h->mb_y, ER_MB_ERROR);



                    return -1;

                }

            }

        }

    }

}

```

### Demonstration

```c

static int decode_slice(H264Context *h){

    MpegEncContext * const s = &h->s;

    const int part_mask= s->partitioned_frame ? (AC_END|AC_ERROR) : 0x7F;



    s->mb_skip_run= -1;



    if( h->pps.cabac ) {

        int i;



        /* realign */

        align_get_bits( &s->gb );



        /* init cabac */

        ff_init_cabac_states( &h->cabac, ff_h264_lps_range, ff_h264_mps_state, ff_h264_lps_state, 64 );

        ff_init_cabac_decoder( &h->cabac,

                               s->gb.buffer + get_bits_count(&s->gb)/8,

                               ( s->gb.size_in_bits - get_bits_count(&s->gb) + 7)/8);

        /* calculate pre-state */

        for( i= 0; i < 460; i++ ) {

            int pre;

            if( h->slice_type == I_TYPE )

                pre = clip( ((cabac_context_init_I[i][0] * s->qscale) >>4 ) + cabac_context_init_I[i][1], 1, 126 );

            else

                pre = clip( ((cabac_context_init_PB[h->cabac_init_idc][i][0] * s->qscale) >>4 ) + cabac_context_init_PB[h->cabac_init_idc][i][1], 1, 126 );



            if( pre <= 63 )

                h->cabac_state[i] = 2 * ( 63 - pre ) + 0;

            else

                h->cabac_state[i] = 2 * ( pre - 64 ) + 1;

        }



        for(;;){

            int ret = decode_mb_cabac(h);

            int eos;



            if(ret>=0) hl_decode_mb(h);



            /* XXX: useless as decode_mb_cabac it doesn't support that ... */

            if( ret >= 0 && h->mb_aff_frame ) { //FIXME optimal? or let mb_decode decode 16x32 ?

                s->mb_y++;



                if(ret>=0) ret = decode_mb_cabac(h);



                hl_decode_mb(h);

                s->mb_y--;

            }

            eos = get_cabac_terminate( &h->cabac );



            if( ret < 0 || h->cabac.bytestream > h->cabac.bytestream_end + 1) {

                av_log(h->s.avctx, AV_LOG_ERROR, "error while decoding MB %d %d\n", s->mb_x, s->mb_y);

                ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x, s->mb_y, (AC_ERROR|DC_ERROR|MV_ERROR)&part_mask);

                return -1;

            }



            if( ++s->mb_x >= s->mb_width ) {

                s->mb_x = 0;

                ff_draw_horiz_band(s, 16*s->mb_y, 16);

                ++s->mb_y;

                if(h->mb_aff_frame) {

                    ++s->mb_y;

                }

            }



            if( eos || s->mb_y >= s->mb_height ) {

                tprintf("slice end %d %d\n", get_bits_count(&s->gb), s->gb.size_in_bits);

                ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x-1, s->mb_y, (AC_END|DC_END|MV_END)&part_mask);

                return 0;

            }

        }



    } else {

        for(;;){

            int ret = decode_mb_cavlc(h);



            if(ret>=0) hl_decode_mb(h);



            if(ret>=0 && h->mb_aff_frame){ //FIXME optimal? or let mb_decode decode 16x32 ?

                s->mb_y++;

                ret = decode_mb_cavlc(h);



                if(ret>=0) hl_decode_mb(h);

                s->mb_y--;

            }



            if(ret<0){

                av_log(h->s.avctx, AV_LOG_ERROR, "error while decoding MB %d %d\n", s->mb_x, s->mb_y);

                ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x, s->mb_y, (AC_ERROR|DC_ERROR|MV_ERROR)&part_mask);



                return -1;

            }



            if(++s->mb_x >= s->mb_width){

                s->mb_x=0;

                ff_draw_horiz_band(s, 16*s->mb_y, 16);

                ++s->mb_y;

                if(h->mb_aff_frame) {

                    ++s->mb_y;

                }

                if(s->mb_y >= s->mb_height){

                    tprintf("slice end %d %d\n", get_bits_count(&s->gb), s->gb.size_in_bits);



                    if(get_bits_count(&s->gb) == s->gb.size_in_bits ) {

                        ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x-1, s->mb_y, (AC_END|DC_END|MV_END)&part_mask);



                        return 0;

                    }else{

                        ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x, s->mb_y, (AC_END|DC_END|MV_END)&part_mask);



                        return -1;

                    }

                }

            }



            if(get_bits_count(&s->gb) >= s->gb.size_in_bits && s->mb_skip_run<=0){

                tprintf("slice end %d %d\n", get_bits_count(&s->gb), s->gb.size_in_bits);

                if(get_bits_count(&s->gb) == s->gb.size_in_bits ){

                    ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x-1, s->mb_y, (AC_END|DC_END|MV_END)&part_mask);



                    return 0;

                }else{

                    ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x, s->mb_y, (AC_ERROR|DC_ERROR|MV_ERROR)&part_mask);



                    return -1;

                }

            }

        }

    }



#if 0

    for(;s->mb_y < s->mb_height; s->mb_y++){

        for(;s->mb_x < s->mb_width; s->mb_x++){

            int ret= decode_mb(h);

            

            hl_decode_mb(h);



            if(ret<0){

                fprintf(stderr, "error while decoding MB %d %d\n", s->mb_x, s->mb_y);

                ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x, s->mb_y, (AC_ERROR|DC_ERROR|MV_ERROR)&part_mask);



                return -1;

            }

        

            if(++s->mb_x >= s->mb_width){

                s->mb_x=0;

                if(++s->mb_y >= s->mb_height){

                    if(get_bits_count(s->gb) == s->gb.size_in_bits){

                        ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x-1, s->mb_y, (AC_END|DC_END|MV_END)&part_mask);



                        return 0;

                    }else{

                        ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x, s->mb_y, (AC_END|DC_END|MV_END)&part_mask);



                        return -1;

                    }

                }

            }

        

            if(get_bits_count(s->?gb) >= s->gb?.size_in_bits){

                if(get_bits_count(s->gb) == s->gb.size_in_bits){

                    ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x-1, s->mb_y, (AC_END|DC_END|MV_END)&part_mask);



                    return 0;

                }else{

                    ff_er_add_slice(s, s->resync_mb_x, s->resync_mb_y, s->mb_x, s->mb_y, (AC_ERROR|DC_ERROR|MV_ERROR)&part_mask);



                    return -1;

                }

            }

        }

        s->mb_x=0;

        ff_draw_horiz_band(s, 16*s->mb_y, 16);

    }

#endif

    return -1; //not reached

}

```

## H2R-020

### Query

```c

static int handle_update_file_cred(int dirfd, const char *name, FsCred *credp)

{

    int fd, ret;

    fd = openat(dirfd, name, O_NONBLOCK | O_NOFOLLOW);

    if (fd < 0) {

        return fd;

    }

    ret = fchmod(fd, credp->fc_mode & 07777);

    if (ret < 0) {

        goto err_out;

    }

    ret = fchownat(fd, "", credp->fc_uid, credp->fc_gid, AT_EMPTY_PATH);

err_out:

    close(fd);

    return ret;

}

```

### Demonstration

```c

static int handle_utimensat(FsContext *ctx, V9fsPath *fs_path,

                            const struct timespec *buf)

{

    int fd, ret;

    struct handle_data *data = (struct handle_data *)ctx->private;



    fd = open_by_handle(data->mountfd, fs_path->data, O_NONBLOCK);

    if (fd < 0) {

        return fd;

    }

    ret = futimens(fd, buf);

    close(fd);

    return ret;

}

```

## H2R-021

### Query

```c

static void rtas_display_character(sPAPREnvironment *spapr,

                                   uint32_t token, uint32_t nargs,

                                   target_ulong args,

                                   uint32_t nret, target_ulong rets)

{

    uint8_t c = rtas_ld(args, 0);

    VIOsPAPRDevice *sdev = vty_lookup(spapr, 0);



    if (!sdev) {

        rtas_st(rets, 0, -1);

    } else {

        vty_putchars(sdev, &c, sizeof(c));

        rtas_st(rets, 0, 0);

    }

}

```

### Demonstration

```c

static void rtas_write_pci_config(sPAPREnvironment *spapr,

                                  uint32_t token, uint32_t nargs,

                                  target_ulong args,

                                  uint32_t nret, target_ulong rets)

{

    uint32_t val, size, addr;

    PCIDevice *dev = find_dev(spapr, 0, rtas_ld(args, 0));



    if (!dev) {

        rtas_st(rets, 0, -1);

        return;

    }

    val = rtas_ld(args, 2);

    size = rtas_ld(args, 1);

    addr = rtas_pci_cfgaddr(rtas_ld(args, 0));

    pci_default_write_config(dev, addr, val, size);

    rtas_st(rets, 0, 0);

}

```

## H2R-022

### Query

```c

static inline int64_t sub64(const int64_t a, const int64_t b)

{

	return a - b;

}

```

### Demonstration

```c

static inline int64_t add64(const int64_t a, const int64_t b)

{

	return a + b;

}

```

## H2R-023

### Query

```c

static int create_ppc_opcodes (CPUPPCState *env, ppc_def_t *def)

{

    opcode_t *opc, *start, *end;



    fill_new_table(env->opcodes, 0x40);

#if defined(PPC_DUMP_CPU)

    printf("* PowerPC instructions for PVR %08x: %s flags %016" PRIx64

           " %08x\n",

           def->pvr, def->name, def->insns_flags, def->flags);

#endif

    if (&opc_start < &opc_end) {

        start = &opc_start;

        end = &opc_end;

    } else {

        start = &opc_end;

        end = &opc_start;

    }

    for (opc = start + 1; opc != end; opc++) {

        if ((opc->handler.type & def->insns_flags) != 0) {

            if (register_insn(env->opcodes, opc) < 0) {

                printf("*** ERROR initializing PowerPC instruction "

                       "0x%02x 0x%02x 0x%02x\n", opc->opc1, opc->opc2,

                       opc->opc3);

                return -1;

            }

#if defined(PPC_DUMP_CPU)

            if (opc1 != 0x00) {

                if (opc->opc3 == 0xFF) {

                    if (opc->opc2 == 0xFF) {

                        printf(" %02x -- -- (%2d ----) : %s\n",

                               opc->opc1, opc->opc1, opc->oname);

                    } else {

                        printf(" %02x %02x -- (%2d %4d) : %s\n",

                               opc->opc1, opc->opc2, opc->opc1, opc->opc2,

                               opc->oname);

                    }

                } else {

                    printf(" %02x %02x %02x (%2d %4d) : %s\n",

                           opc->opc1, opc->opc2, opc->opc3,

                           opc->opc1, (opc->opc3 << 5) | opc->opc2,

                           opc->oname);

                }

            }

#endif

        }

    }

    fix_opcode_tables(env->opcodes);

    fflush(stdout);

    fflush(stderr);



    return 0;

}

```

### Demonstration

```c

static int dump_ppc_insns (CPUPPCState *env)

{

    opc_handler_t **table, *handler;

    uint8_t opc1, opc2, opc3;



    printf("Instructions set:\n");

    /* opc1 is 6 bits long */

    for (opc1 = 0x00; opc1 < 0x40; opc1++) {

        table = env->opcodes;

        handler = table[opc1];

        if (is_indirect_opcode(handler)) {

            /* opc2 is 5 bits long */

            for (opc2 = 0; opc2 < 0x20; opc2++) {

                table = env->opcodes;

                handler = env->opcodes[opc1];

                table = ind_table(handler);

                handler = table[opc2];

                if (is_indirect_opcode(handler)) {

                    table = ind_table(handler);

                    /* opc3 is 5 bits long */

                    for (opc3 = 0; opc3 < 0x20; opc3++) {

                        handler = table[opc3];

                        if (handler->handler != &gen_invalid) {

                            printf("INSN: %02x %02x %02x (%02d %04d) : %s\n",

                                   opc1, opc2, opc3, opc1, (opc3 << 5) | opc2,

                                   handler->oname);

                        }

                    }

                } else {

                    if (handler->handler != &gen_invalid) {

                        printf("INSN: %02x %02x -- (%02d %04d) : %s\n",

                               opc1, opc2, opc1, opc2, handler->oname);

                    }

                }

            }

        } else {

            if (handler->handler != &gen_invalid) {

                printf("INSN: %02x -- -- (%02d ----) : %s\n",

                       opc1, opc1, handler->oname);

            }

        }

    }

}

```

## H2R-024

### Query

```c

static int decode0(GetByteContext *gb, RangeCoder *rc, unsigned cumFreq, unsigned freq, unsigned total_freq)

{

    int t;



    if (total_freq == 0)

        return AVERROR_INVALIDDATA;



    t = rc->range * (uint64_t)cumFreq / total_freq;



    rc->code1 += t + 1;

    rc->range = rc->range * (uint64_t)(freq + cumFreq) / total_freq - (t + 1);



    while (rc->range < TOP && bytestream2_get_bytes_left(gb) > 0) {

        unsigned byte = bytestream2_get_byte(gb);

        rc->code = (rc->code << 8) | byte;

        rc->code1 <<= 8;

        rc->range <<= 8;

    }



    return 0;

}

```

### Demonstration

```c

static void decode(GetByteContext *gb, RangeCoder *rc, unsigned cumFreq, unsigned freq, unsigned total_freq)

{

    rc->code -= cumFreq * rc->range;

    rc->range *= freq;



    while (rc->range < TOP && bytestream2_get_bytes_left(gb) > 0) {

        unsigned byte = bytestream2_get_byte(gb);

        rc->code = (rc->code << 8) | byte;

        rc->range <<= 8;

    }

}

```

## H2R-025

### Query

```c

static int config_props(AVFilterLink *outlink)

{

    AVFilterContext *ctx = outlink->src;

    AVFilterLink *inlink = outlink->src->inputs[0];

    ScaleContext *scale = ctx->priv;

    int64_t w, h;



    if (!(w = scale->w))

        w = inlink->w;

    if (!(h = scale->h))

        h = inlink->h;

    if (w == -1)

        w = av_rescale(h, inlink->w, inlink->h);

    if (h == -1)

        h = av_rescale(w, inlink->h, inlink->w);



    if (w > INT_MAX || h > INT_MAX ||

        (h * inlink->w) > INT_MAX  ||

        (w * inlink->h) > INT_MAX)

        av_log(ctx, AV_LOG_ERROR, "Rescaled value for width or height is too big.\n");



    outlink->w = w;

    outlink->h = h;



    /* TODO: make algorithm configurable */

    scale->sws = sws_getContext(inlink ->w, inlink ->h, inlink ->format,

                                outlink->w, outlink->h, outlink->format,

                                SWS_BILINEAR, NULL, NULL, NULL);



    av_log(ctx, AV_LOG_INFO, "w:%d h:%d fmt:%s\n",

           outlink->w, outlink->h, av_pix_fmt_descriptors[outlink->format].name);



    scale->input_is_pal = inlink->format == PIX_FMT_PAL8      ||

                          inlink->format == PIX_FMT_BGR4_BYTE ||

                          inlink->format == PIX_FMT_RGB4_BYTE ||

                          inlink->format == PIX_FMT_BGR8      ||

                          inlink->format == PIX_FMT_RGB8;



    return !scale->sws;

}

```

### Demonstration

```c

static void start_frame(AVFilterLink *link, AVFilterPicRef *picref)

{

    CropContext *crop = link->dst->priv;

    AVFilterPicRef *ref2 = avfilter_ref_pic(picref, ~0);

    int i;



    ref2->w        = crop->w;

    ref2->h        = crop->h;



    ref2->data[0] += crop->y * ref2->linesize[0];

    ref2->data[0] += (crop->x * crop->bpp) >> 3;



    if (link->format != PIX_FMT_PAL8      &&

        link->format != PIX_FMT_BGR4_BYTE &&

        link->format != PIX_FMT_RGB4_BYTE &&

        link->format != PIX_FMT_BGR8      &&

        link->format != PIX_FMT_RGB8) {

        for (i = 1; i < 3; i ++) {

            if (ref2->data[i]) {

                ref2->data[i] += (crop->y >> crop->vsub) * ref2->linesize[i];

                ref2->data[i] += ((crop->x * crop->bpp) >> 3) >> crop->hsub;

            }

        }

    }



    /* alpha plane */

    if (ref2->data[3]) {

        ref2->data[3] += crop->y * ref2->linesize[3];

        ref2->data[3] += (crop->x * crop->bpp) >> 3;

    }



    avfilter_start_frame(link->dst->outputs[0], ref2);

}

```

## H2R-026

### Query

```c

static int motion_inter_4v_block (bit_buffer_t *bitbuf,

				  uint8_t *current, uint8_t *previous, int pitch,

				  svq1_pmv_t *motion,int x, int y) {

  uint8_t    *src;

  uint8_t    *dst;

  svq1_pmv_t  mv;

  svq1_pmv_t *pmv[4];

  int	      i, result;



  /* predict and decode motion vector (0) */

  pmv[0] = &motion[0];

  pmv[1] = &motion[(x / 8) + 2];

  pmv[2] = &motion[(x / 8) + 4];



  if (y == 0) {

    pmv[1] = pmv[0];

    pmv[2] = pmv[0];

  }



  result = decode_motion_vector (bitbuf, &mv, pmv);



  if (result != 0)

    return result;



  /* predict and decode motion vector (1) */

  pmv[0] = &mv;

  pmv[1] = &motion[(x / 8) + 3];



  if (y == 0) {

    pmv[1] = pmv[0];

    pmv[2] = pmv[0];

  }



  result = decode_motion_vector (bitbuf, &motion[0], pmv);



  if (result != 0)

    return result;



  /* predict and decode motion vector (2) */

  pmv[1] = &motion[0];

  pmv[2] = &motion[(x / 8) + 1];



  result = decode_motion_vector (bitbuf, &motion[(x / 8) + 2], pmv);



  if (result != 0)

    return result;



  /* predict and decode motion vector (3) */

  pmv[2] = &motion[(x / 8) + 2];

  pmv[3] = &motion[(x / 8) + 3];



  result = decode_motion_vector (bitbuf, pmv[3], pmv);



  if (result != 0)

    return result;



  /* form predictions */

  for (i=0; i < 4; i++) {

    src = &previous[(x + (pmv[i]->x >> 1)) + (y + (pmv[i]->y >> 1))*pitch];

    dst = current;



    put_pixels_tab[((pmv[i]->y & 1) << 1) | (pmv[i]->x & 1)](dst,src,pitch,8);



    /* select next block */

    if (i & 1) {

      current  += 8*(pitch - 1);

      previous += 8*(pitch - 1);

    } else {

      current  += 8;

      previous += 8;

    }

  }



  return 0;

}

```

### Demonstration

```c

static int svq1_motion_inter_4v_block(DSPContext *dsp, GetBitContext *bitbuf,

                                      uint8_t *current, uint8_t *previous,

                                      int pitch, svq1_pmv *motion, int x, int y)

{

    uint8_t *src;

    uint8_t *dst;

    svq1_pmv mv;

    svq1_pmv *pmv[4];

    int i, result;



    /* predict and decode motion vector (0) */

    pmv[0] = &motion[0];

    if (y == 0) {

        pmv[1] =

        pmv[2] = pmv[0];

    } else {

        pmv[1] = &motion[(x / 8) + 2];

        pmv[2] = &motion[(x / 8) + 4];

    }



    result = svq1_decode_motion_vector(bitbuf, &mv, pmv);



    if (result != 0)

        return result;



    /* predict and decode motion vector (1) */

    pmv[0] = &mv;

    if (y == 0) {

        pmv[1] =

        pmv[2] = pmv[0];

    } else {

        pmv[1] = &motion[(x / 8) + 3];

    }

    result = svq1_decode_motion_vector(bitbuf, &motion[0], pmv);



    if (result != 0)

        return result;



    /* predict and decode motion vector (2) */

    pmv[1] = &motion[0];

    pmv[2] = &motion[(x / 8) + 1];



    result = svq1_decode_motion_vector(bitbuf, &motion[(x / 8) + 2], pmv);



    if (result != 0)

        return result;



    /* predict and decode motion vector (3) */

    pmv[2] = &motion[(x / 8) + 2];

    pmv[3] = &motion[(x / 8) + 3];



    result = svq1_decode_motion_vector(bitbuf, pmv[3], pmv);



    if (result != 0)

        return result;



    /* form predictions */

    for (i = 0; i < 4; i++) {

        int mvx = pmv[i]->x + (i  & 1) * 16;

        int mvy = pmv[i]->y + (i >> 1) * 16;



        // FIXME: clipping or padding?

        if (y + (mvy >> 1) < 0)

            mvy = 0;

        if (x + (mvx >> 1) < 0)

            mvx = 0;



        src = &previous[(x + (mvx >> 1)) + (y + (mvy >> 1)) * pitch];

        dst = current;



        dsp->put_pixels_tab[1][((mvy & 1) << 1) | (mvx & 1)](dst, src, pitch, 8);



        /* select next block */

        if (i & 1)

            current += 8 * (pitch - 1);

        else

            current += 8;

    }



    return 0;

}

```

## H2R-027

### Query

```c

static void xendev_class_init(ObjectClass *klass, void *data)

{

    DeviceClass *dc = DEVICE_CLASS(klass);



    dc->props = xendev_properties;

    set_bit(DEVICE_CATEGORY_MISC, dc->categories);






}

```

### Demonstration

```c

static void sun4m_fdc_class_init(ObjectClass *klass, void *data)

{

    DeviceClass *dc = DEVICE_CLASS(klass);



    dc->props = sun4m_fdc_properties;

    set_bit(DEVICE_CATEGORY_STORAGE, dc->categories);






}

```

## H2R-028

### Query

```c

static void pc_dimm_check_memdev_is_busy(Object *obj, const char *name,

                                      Object *val, Error **errp)

{

    MemoryRegion *mr;



    mr = host_memory_backend_get_memory(MEMORY_BACKEND(val), errp);

    if (memory_region_is_mapped(mr)) {

        char *path = object_get_canonical_path_component(val);

        error_setg(errp, "can't use already busy memdev: %s", path);

        g_free(path);

    } else {

        qdev_prop_allow_set_link_before_realize(obj, name, val, errp);

    }

}

```

### Demonstration

```c

static void pc_dimm_check_memdev_is_busy(Object *obj, const char *name,

                                      Object *val, Error **errp)

{

    MemoryRegion *mr;

    Error *local_err = NULL;



    mr = host_memory_backend_get_memory(MEMORY_BACKEND(val), &local_err);

    if (local_err) {

        goto out;

    }

    if (memory_region_is_mapped(mr)) {

        char *path = object_get_canonical_path_component(val);

        error_setg(&local_err, "can't use already busy memdev: %s", path);

        g_free(path);

    } else {

        qdev_prop_allow_set_link_before_realize(obj, name, val, &local_err);

    }



out:

    error_propagate(errp, local_err);

}

```

## H2R-029

### Query

```c

static int mpeg_mux_end(AVFormatContext *ctx)

{

    StreamInfo *stream;

    int i;



    /* flush each packet */

    for(i=0;i<ctx->nb_streams;i++) {

        stream = ctx->streams[i]->priv_data;

        if (stream->buffer_ptr > 0) {

            if (i == (ctx->nb_streams - 1)) 

                flush_packet(ctx, i, 1);

            else

                flush_packet(ctx, i, 0);

        }

    }



    /* write the end header */

    //put_be32(&ctx->pb, ISO_11172_END_CODE);

    //put_flush_packet(&ctx->pb);



    for(i=0;i<ctx->nb_streams;i++)

        av_freep(&ctx->streams[i]->priv_data);



    return 0;

}

```

### Demonstration

```c

static int handle_packets(MpegTSContext *ts, int nb_packets)

{

    AVFormatContext *s = ts->stream;

    uint8_t packet[TS_PACKET_SIZE];

    int packet_num, ret = 0;



    if (avio_tell(s->pb) != ts->last_pos) {

        int i;

        av_dlog("Skipping after seek\n");

        /* seek detected, flush pes buffer */

        for (i = 0; i < NB_PID_MAX; i++) {

            if (ts->pids[i] && ts->pids[i]->type == MPEGTS_PES) {

                PESContext *pes = ts->pids[i]->u.pes_filter.opaque;

                av_freep(&pes->buffer);

                ts->pids[i]->last_cc = -1;

                pes->data_index = 0;

                pes->state = MPEGTS_SKIP; /* skip until pes header */

            }

        }

    }



    ts->stop_parse = 0;

    packet_num = 0;

    for(;;) {

        if (ts->stop_parse>0)

            break;

        packet_num++;

        if (nb_packets != 0 && packet_num >= nb_packets)

            break;

        ret = read_packet(s, packet, ts->raw_packet_size);

        if (ret != 0)

            break;

        ret = handle_packet(ts, packet);

        if (ret != 0)

            break;

    }

    ts->last_pos = avio_tell(s->pb);

    return ret;

}

```

## H2R-030

### Query

```c

static void gen_exception_return(DisasContext *s, TCGv pc)

{

    TCGv tmp;

    store_reg(s, 15, pc);

    tmp = load_cpu_field(spsr);

    gen_set_cpsr(tmp, 0xffffffff);

    dead_tmp(tmp);

    s->is_jmp = DISAS_UPDATE;

}

```

### Demonstration

```c

static void gen_exception_return(DisasContext *s, TCGv_i32 pc)

{

    TCGv_i32 tmp;

    store_reg(s, 15, pc);

    tmp = load_cpu_field(spsr);

    gen_set_cpsr(tmp, CPSR_ERET_MASK);

    tcg_temp_free_i32(tmp);

    s->is_jmp = DISAS_JUMP;

}

```

## H2R-031

### Query

```c

static void cs_write (void *opaque, target_phys_addr_t addr,

                      uint64_t val64, unsigned size)

{

    CSState *s = opaque;

    uint32_t saddr, iaddr, val;



    saddr = addr;

    val = val64;



    switch (saddr) {

    case Index_Address:

        if (!(s->regs[Index_Address] & MCE) && (val & MCE)

            && (s->dregs[Interface_Configuration] & (3 << 3)))

            s->aci_counter = conf.aci_counter;



        s->regs[Index_Address] = val & ~(1 << 7);

        break;



    case Index_Data:

        if (!(s->dregs[MODE_And_ID] & MODE2))

            iaddr = s->regs[Index_Address] & 0x0f;

        else

            iaddr = s->regs[Index_Address] & 0x1f;



        switch (iaddr) {

        case RESERVED:

        case RESERVED_2:

        case RESERVED_3:

            lwarn ("attempt to write %#x to reserved indirect register %d\n",

                   val, iaddr);

            break;



        case FS_And_Playback_Data_Format:

            if (s->regs[Index_Address] & MCE) {

                cs_reset_voices (s, val);

            }

            else {

                if (s->dregs[Alternate_Feature_Status] & PMCE) {

                    val = (val & ~0x0f) | (s->dregs[iaddr] & 0x0f);

                    cs_reset_voices (s, val);

                }

                else {

                    lwarn ("[P]MCE(%#x, %#x) is not set, val=%#x\n",

                           s->regs[Index_Address],

                           s->dregs[Alternate_Feature_Status],

                           val);

                    break;

                }

            }

            s->dregs[iaddr] = val;

            break;



        case Interface_Configuration:

            val &= ~(1 << 5);   /* D5 is reserved */

            s->dregs[iaddr] = val;

            if (val & PPIO) {

                lwarn ("PIO is not supported (%#x)\n", val);

                break;

            }

            if (val & PEN) {

                if (!s->dma_running) {

                    cs_reset_voices (s, s->dregs[FS_And_Playback_Data_Format]);

                }

            }

            else {

                if (s->dma_running) {

                    DMA_release_DREQ (s->dma);

                    AUD_set_active_out (s->voice, 0);

                    s->dma_running = 0;

                }

            }

            break;



        case Error_Status_And_Initialization:

            lwarn ("attempt to write to read only register %d\n", iaddr);

            break;



        case MODE_And_ID:

            dolog ("val=%#x\n", val);

            if (val & MODE2)

                s->dregs[iaddr] |= MODE2;

            else

                s->dregs[iaddr] &= ~MODE2;

            break;



        case Alternate_Feature_Enable_I:

            if (val & TE)

                lerr ("timer is not yet supported\n");

            s->dregs[iaddr] = val;

            break;



        case Alternate_Feature_Status:

            if ((s->dregs[iaddr] & PI) && !(val & PI)) {

                /* XXX: TI CI */

                qemu_irq_lower (s->pic);

                s->regs[Status] &= ~INT;

            }

            s->dregs[iaddr] = val;

            break;



        case Version_Chip_ID:

            lwarn ("write to Version_Chip_ID register %#x\n", val);

            s->dregs[iaddr] = val;

            break;



        default:

            s->dregs[iaddr] = val;

            break;

        }

        dolog ("written value %#x to indirect register %d\n", val, iaddr);

        break;



    case Status:

        if (s->regs[Status] & INT) {

            qemu_irq_lower (s->pic);

        }

        s->regs[Status] &= ~INT;

        s->dregs[Alternate_Feature_Status] &= ~(PI | CI | TI);

        break;



    case PIO_Data:

        lwarn ("attempt to write value %#x to PIO register\n", val);

        break;

    }

}

```

### Demonstration

```c

static void pxa2xx_fir_write(void *opaque, hwaddr addr,

                             uint64_t value64, unsigned size)

{

    PXA2xxFIrState *s = (PXA2xxFIrState *) opaque;

    uint32_t value = value64;

    uint8_t ch;



    switch (addr) {

    case ICCR0:

        s->control[0] = value;

        if (!(value & (1 << 4)))			/* RXE */

            s->rx_len = s->rx_start = 0;

        if (!(value & (1 << 3))) {                      /* TXE */

            /* Nop */

        }

        s->enable = value & 1;				/* ITR */

        if (!s->enable)

            s->status[0] = 0;

        pxa2xx_fir_update(s);

        break;

    case ICCR1:

        s->control[1] = value;

        break;

    case ICCR2:

        s->control[2] = value & 0x3f;

        pxa2xx_fir_update(s);

        break;

    case ICDR:

        if (s->control[2] & (1 << 2)) { /* TXP */

            ch = value;

        } else {

            ch = ~value;

        }

        if (s->enable && (s->control[0] & (1 << 3))) { /* TXE */

            /* XXX this blocks entire thread. Rewrite to use

             * qemu_chr_fe_write and background I/O callbacks */

            qemu_chr_fe_write_all(&s->chr, &ch, 1);

        }

        break;

    case ICSR0:

        s->status[0] &= ~(value & 0x66);

        pxa2xx_fir_update(s);

        break;

    case ICFOR:

        break;

    default:

        printf("%s: Bad register " REG_FMT "\n", __FUNCTION__, addr);

    }

}

```

## H2R-032

### Query

```c

static int tta_decode_frame(AVCodecContext *avctx,

        void *data, int *data_size,

        AVPacket *avpkt)

{

    const uint8_t *buf = avpkt->data;

    int buf_size = avpkt->size;

    TTAContext *s = avctx->priv_data;

    int i;



    init_get_bits(&s->gb, buf, buf_size*8);

    {

        int32_t predictors[s->channels];

        TTAFilter filters[s->channels];

        TTARice rices[s->channels];

        int cur_chan = 0, framelen = s->frame_length;

        int32_t *p;



        // FIXME: seeking

        s->total_frames--;

        if (!s->total_frames && s->last_frame_length)

            framelen = s->last_frame_length;



        // init per channel states

        for (i = 0; i < s->channels; i++) {

            predictors[i] = 0;

            ttafilter_init(&(filters[i]), ttafilter_configs[s->bps-1][0], ttafilter_configs[s->bps-1][1]);

            rice_init(&(rices[i]), 10, 10);

        }



        for (p = s->decode_buffer; p < s->decode_buffer + (framelen * s->channels); p++) {

            int32_t *predictor = &(predictors[cur_chan]);

            TTAFilter *filter = &(filters[cur_chan]);

            TTARice *rice = &(rices[cur_chan]);

            uint32_t unary, depth, k;

            int32_t value;



            unary = tta_get_unary(&s->gb);



            if (unary == 0) {

                depth = 0;

                k = rice->k0;

            } else {

                depth = 1;

                k = rice->k1;

                unary--;

            }



            if (k)

                value = (unary << k) + get_bits(&s->gb, k);

            else

                value = unary;



            // FIXME: copy paste from original

            switch (depth) {

            case 1:

                rice->sum1 += value - (rice->sum1 >> 4);

                if (rice->k1 > 0 && rice->sum1 < shift_16[rice->k1])

                    rice->k1--;

                else if(rice->sum1 > shift_16[rice->k1 + 1])

                    rice->k1++;

                value += shift_1[rice->k0];

            default:

                rice->sum0 += value - (rice->sum0 >> 4);

                if (rice->k0 > 0 && rice->sum0 < shift_16[rice->k0])

                    rice->k0--;

                else if(rice->sum0 > shift_16[rice->k0 + 1])

                    rice->k0++;

            }



            // extract coded value

#define UNFOLD(x) (((x)&1) ? (++(x)>>1) : (-(x)>>1))

            *p = UNFOLD(value);



            // run hybrid filter

            ttafilter_process(filter, p, 0);



            // fixed order prediction

#define PRED(x, k) (int32_t)((((uint64_t)x << k) - x) >> k)

            switch (s->bps) {

                case 1: *p += PRED(*predictor, 4); break;

                case 2:

                case 3: *p += PRED(*predictor, 5); break;

                case 4: *p += *predictor; break;

            }

            *predictor = *p;



#if 0

            // extract 32bit float from last two int samples

            if (s->is_float && ((p - data) & 1)) {

                uint32_t neg = *p & 0x80000000;

                uint32_t hi = *(p - 1);

                uint32_t lo = abs(*p) - 1;



                hi += (hi || lo) ? 0x3f80 : 0;

                // SWAP16: swap all the 16 bits

                *(p - 1) = (hi << 16) | SWAP16(lo) | neg;

            }

#endif



            /*if ((get_bits_count(&s->gb)+7)/8 > buf_size)

            {

                av_log(NULL, AV_LOG_INFO, "overread!!\n");

                break;

            }*/



            // flip channels

            if (cur_chan < (s->channels-1))

                cur_chan++;

            else {

                // decorrelate in case of stereo integer

                if (!s->is_float && (s->channels > 1)) {

                    int32_t *r = p - 1;

                    for (*p += *r / 2; r > p - s->channels; r--)

                        *r = *(r + 1) - *r;

                }

                cur_chan = 0;

            }

        }



        skip_bits(&s->gb, 32); // frame crc



        // convert to output buffer

        switch(s->bps) {

            case 2: {

                uint16_t *samples = data;

                for (p = s->decode_buffer; p < s->decode_buffer + (framelen * s->channels); p++) {

//                    *samples++ = (unsigned char)*p;

//                    *samples++ = (unsigned char)(*p >> 8);

                    *samples++ = *p;

                }

                *data_size = (uint8_t *)samples - (uint8_t *)data;

                break;

            }

            default:

                av_log(s->avctx, AV_LOG_ERROR, "Error, only 16bit samples supported!\n");

        }

    }



//    return get_bits_count(&s->gb)+7)/8;

    return buf_size;

}

```

### Demonstration

```c

static int tta_decode_frame(AVCodecContext *avctx, void *data,

                            int *got_frame_ptr, AVPacket *avpkt)

{

    const uint8_t *buf = avpkt->data;

    int buf_size = avpkt->size;

    TTAContext *s = avctx->priv_data;

    int i, ret;

    int cur_chan = 0, framelen = s->frame_length;

    int32_t *p;



    if (avctx->err_recognition & AV_EF_CRCCHECK) {

        if (buf_size < 4 || tta_check_crc(s, buf, buf_size - 4))

            return AVERROR_INVALIDDATA;

    }



    init_get_bits(&s->gb, buf, buf_size*8);



    // FIXME: seeking

    s->total_frames--;

    if (!s->total_frames && s->last_frame_length)

        framelen = s->last_frame_length;



    /* get output buffer */

    s->frame.nb_samples = framelen;

    if ((ret = ff_get_buffer(avctx, &s->frame)) < 0) {

        av_log(avctx, AV_LOG_ERROR, "get_buffer() failed\n");

        return ret;

    }



    // decode directly to output buffer for 24-bit sample format

    if (s->bps == 3)

        s->decode_buffer = (int32_t *)s->frame.data[0];



    // init per channel states

    for (i = 0; i < s->channels; i++) {

        s->ch_ctx[i].predictor = 0;

        ttafilter_init(&s->ch_ctx[i].filter, ttafilter_configs[s->bps-1]);

        rice_init(&s->ch_ctx[i].rice, 10, 10);

    }



    for (p = s->decode_buffer; p < s->decode_buffer + (framelen * s->channels); p++) {

        int32_t *predictor = &s->ch_ctx[cur_chan].predictor;

        TTAFilter *filter = &s->ch_ctx[cur_chan].filter;

        TTARice *rice = &s->ch_ctx[cur_chan].rice;

        uint32_t unary, depth, k;

        int32_t value;



        unary = tta_get_unary(&s->gb);



        if (unary == 0) {

            depth = 0;

            k = rice->k0;

        } else {

            depth = 1;

            k = rice->k1;

            unary--;

        }



        if (get_bits_left(&s->gb) < k) {

            ret = AVERROR_INVALIDDATA;

            goto error;

        }



        if (k) {

            if (k > MIN_CACHE_BITS) {

                ret = AVERROR_INVALIDDATA;

                goto error;

            }

            value = (unary << k) + get_bits(&s->gb, k);

        } else

            value = unary;



        // FIXME: copy paste from original

        switch (depth) {

        case 1:

            rice->sum1 += value - (rice->sum1 >> 4);

            if (rice->k1 > 0 && rice->sum1 < shift_16[rice->k1])

                rice->k1--;

            else if(rice->sum1 > shift_16[rice->k1 + 1])

                rice->k1++;

            value += shift_1[rice->k0];

        default:

            rice->sum0 += value - (rice->sum0 >> 4);

            if (rice->k0 > 0 && rice->sum0 < shift_16[rice->k0])

                rice->k0--;

            else if(rice->sum0 > shift_16[rice->k0 + 1])

                rice->k0++;

        }



        // extract coded value

        *p = 1 + ((value >> 1) ^ ((value & 1) - 1));



        // run hybrid filter

        ttafilter_process(filter, p);



        // fixed order prediction

#define PRED(x, k) (int32_t)((((uint64_t)x << k) - x) >> k)

        switch (s->bps) {

        case 1: *p += PRED(*predictor, 4); break;

        case 2:

        case 3: *p += PRED(*predictor, 5); break;

        case 4: *p +=      *predictor;     break;

        }

        *predictor = *p;



        // flip channels

        if (cur_chan < (s->channels-1))

            cur_chan++;

        else {

            // decorrelate in case of multiple channels

            if (s->channels > 1) {

                int32_t *r = p - 1;

                for (*p += *r / 2; r > p - s->channels; r--)

                    *r = *(r + 1) - *r;

            }

            cur_chan = 0;

        }

    }



    if (get_bits_left(&s->gb) < 32) {

        ret = AVERROR_INVALIDDATA;

        goto error;

    }

    skip_bits_long(&s->gb, 32); // frame crc



    // convert to output buffer

    if (s->bps == 2) {

        int16_t *samples = (int16_t *)s->frame.data[0];

        for (p = s->decode_buffer; p < s->decode_buffer + (framelen * s->channels); p++)

            *samples++ = *p;

    } else {

        // shift samples for 24-bit sample format

        int32_t *samples = (int32_t *)s->frame.data[0];

        for (i = 0; i < framelen * s->channels; i++)

            *samples++ <<= 8;

        // reset decode buffer

        s->decode_buffer = NULL;

    }



    *got_frame_ptr   = 1;

    *(AVFrame *)data = s->frame;



    return buf_size;

error:

    // reset decode buffer

    if (s->bps == 3)

        s->decode_buffer = NULL;

    return ret;

}

```

## H2R-033

### Query

```c

static int h264_slice_header_parse(H264Context *h, H264SliceContext *sl,

                                   const H2645NAL *nal)

{

    const SPS *sps;

    const PPS *pps;

    int ret;

    unsigned int slice_type, tmp, i;

    int field_pic_flag, bottom_field_flag;

    int frame_num, droppable, picture_structure;

    int mb_aff_frame = 0;



    sl->first_mb_addr = get_ue_golomb(&sl->gb);



    if (sl->first_mb_addr == 0) { // FIXME better field boundary detection

        if (h->current_slice && h->cur_pic_ptr && FIELD_PICTURE(h)) {

            ff_h264_field_end(h, sl, 1);

        }



        h->current_slice = 0;

        if (!h->first_field) {

            if (h->cur_pic_ptr && !h->droppable) {

                ff_thread_report_progress(&h->cur_pic_ptr->tf, INT_MAX,

                                          h->picture_structure == PICT_BOTTOM_FIELD);

            }

            h->cur_pic_ptr = NULL;

        }

    }



    slice_type = get_ue_golomb_31(&sl->gb);

    if (slice_type > 9) {

        av_log(h->avctx, AV_LOG_ERROR,

               "slice type %d too large at %d\n",

               slice_type, sl->first_mb_addr);

        return AVERROR_INVALIDDATA;

    }

    if (slice_type > 4) {

        slice_type -= 5;

        sl->slice_type_fixed = 1;

    } else

        sl->slice_type_fixed = 0;



    slice_type         = ff_h264_golomb_to_pict_type[slice_type];

    sl->slice_type     = slice_type;

    sl->slice_type_nos = slice_type & 3;



    if (nal->type  == NAL_IDR_SLICE &&

        sl->slice_type_nos != AV_PICTURE_TYPE_I) {

        av_log(h->avctx, AV_LOG_ERROR, "A non-intra slice in an IDR NAL unit.\n");

        return AVERROR_INVALIDDATA;

    }



    sl->pps_id = get_ue_golomb(&sl->gb);

    if (sl->pps_id >= MAX_PPS_COUNT) {

        av_log(h->avctx, AV_LOG_ERROR, "pps_id %u out of range\n", sl->pps_id);

        return AVERROR_INVALIDDATA;

    }

    if (!h->ps.pps_list[sl->pps_id]) {

        av_log(h->avctx, AV_LOG_ERROR,

               "non-existing PPS %u referenced\n",

               sl->pps_id);

        return AVERROR_INVALIDDATA;

    }

    if (h->current_slice > 0 &&

        h->ps.pps != (const PPS*)h->ps.pps_list[sl->pps_id]->data) {

        av_log(h->avctx, AV_LOG_ERROR, "PPS changed between slices\n");

        return AVERROR_INVALIDDATA;

    }

    pps = (const PPS*)h->ps.pps_list[sl->pps_id]->data;



    if (!h->ps.sps_list[pps->sps_id]) {

        av_log(h->avctx, AV_LOG_ERROR,

               "non-existing SPS %u referenced\n", pps->sps_id);

        return AVERROR_INVALIDDATA;

    }

    sps = (const SPS*)h->ps.sps_list[pps->sps_id]->data;



    frame_num = get_bits(&sl->gb, sps->log2_max_frame_num);

    if (!h->setup_finished)

        h->poc.frame_num = frame_num;



    sl->mb_mbaff       = 0;



    droppable = nal->ref_idc == 0;

    if (sps->frame_mbs_only_flag) {

        picture_structure = PICT_FRAME;

    } else {

        field_pic_flag = get_bits1(&sl->gb);

        if (field_pic_flag) {

            bottom_field_flag = get_bits1(&sl->gb);

            picture_structure = PICT_TOP_FIELD + bottom_field_flag;

        } else {

            picture_structure = PICT_FRAME;

            mb_aff_frame      = sps->mb_aff;

        }

    }

    if (!h->setup_finished) {

        h->mb_aff_frame      = mb_aff_frame;

    }

    sl->picture_structure      = picture_structure;

    sl->mb_field_decoding_flag = picture_structure != PICT_FRAME;



    if (h->current_slice != 0) {

        if (h->picture_structure != picture_structure ||

            h->droppable         != droppable) {

            av_log(h->avctx, AV_LOG_ERROR,

                   "Changing field mode (%d -> %d) between slices is not allowed\n",

                   h->picture_structure, picture_structure);

            return AVERROR_INVALIDDATA;

        } else if (!h->cur_pic_ptr) {

            av_log(h->avctx, AV_LOG_ERROR,

                   "unset cur_pic_ptr on slice %d\n",

                   h->current_slice + 1);

            return AVERROR_INVALIDDATA;

        }

    }



    if (picture_structure == PICT_FRAME) {

        h->curr_pic_num = h->poc.frame_num;

        h->max_pic_num  = 1 << sps->log2_max_frame_num;

    } else {

        h->curr_pic_num = 2 * h->poc.frame_num + 1;

        h->max_pic_num  = 1 << (sps->log2_max_frame_num + 1);

    }



    if (nal->type == NAL_IDR_SLICE)

        get_ue_golomb(&sl->gb); /* idr_pic_id */



    if (sps->poc_type == 0) {

        int poc_lsb = get_bits(&sl->gb, sps->log2_max_poc_lsb);



        if (!h->setup_finished)

            h->poc.poc_lsb = poc_lsb;



        if (pps->pic_order_present == 1 && picture_structure == PICT_FRAME) {

            int delta_poc_bottom = get_se_golomb(&sl->gb);

            if (!h->setup_finished)

                h->poc.delta_poc_bottom = delta_poc_bottom;

        }

    }



    if (sps->poc_type == 1 && !sps->delta_pic_order_always_zero_flag) {

        int delta_poc = get_se_golomb(&sl->gb);



        if (!h->setup_finished)

            h->poc.delta_poc[0] = delta_poc;



        if (pps->pic_order_present == 1 && picture_structure == PICT_FRAME) {

            delta_poc = get_se_golomb(&sl->gb);



            if (!h->setup_finished)

                h->poc.delta_poc[1] = delta_poc;

        }

    }



    if (pps->redundant_pic_cnt_present)

        sl->redundant_pic_count = get_ue_golomb(&sl->gb);



    if (sl->slice_type_nos == AV_PICTURE_TYPE_B)

        sl->direct_spatial_mv_pred = get_bits1(&sl->gb);



    ret = ff_h264_parse_ref_count(&sl->list_count, sl->ref_count,

                                  &sl->gb, pps, sl->slice_type_nos,

                                  picture_structure);

    if (ret < 0)

        return ret;



    if (sl->slice_type_nos != AV_PICTURE_TYPE_I) {

       ret = ff_h264_decode_ref_pic_list_reordering(h, sl);

       if (ret < 0) {

           sl->ref_count[1] = sl->ref_count[0] = 0;

           return ret;

       }

    }



    sl->pwt.use_weight = 0;

    for (i = 0; i < 2; i++) {

        sl->pwt.luma_weight_flag[i]   = 0;

        sl->pwt.chroma_weight_flag[i] = 0;

    }

    if ((pps->weighted_pred && sl->slice_type_nos == AV_PICTURE_TYPE_P) ||

        (pps->weighted_bipred_idc == 1 &&

         sl->slice_type_nos == AV_PICTURE_TYPE_B))

        ff_h264_pred_weight_table(&sl->gb, sps, sl->ref_count,

                                  sl->slice_type_nos, &sl->pwt);



    sl->explicit_ref_marking = 0;

    if (nal->ref_idc) {

        ret = ff_h264_decode_ref_pic_marking(h, sl, &sl->gb);

        if (ret < 0 && (h->avctx->err_recognition & AV_EF_EXPLODE))

            return AVERROR_INVALIDDATA;

    }



    if (sl->slice_type_nos != AV_PICTURE_TYPE_I && pps->cabac) {

        tmp = get_ue_golomb_31(&sl->gb);

        if (tmp > 2) {

            av_log(h->avctx, AV_LOG_ERROR, "cabac_init_idc %u overflow\n", tmp);

            return AVERROR_INVALIDDATA;

        }

        sl->cabac_init_idc = tmp;

    }



    sl->last_qscale_diff = 0;

    tmp = pps->init_qp + get_se_golomb(&sl->gb);

    if (tmp > 51 + 6 * (sps->bit_depth_luma - 8)) {

        av_log(h->avctx, AV_LOG_ERROR, "QP %u out of range\n", tmp);

        return AVERROR_INVALIDDATA;

    }

    sl->qscale       = tmp;

    sl->chroma_qp[0] = get_chroma_qp(pps, 0, sl->qscale);

    sl->chroma_qp[1] = get_chroma_qp(pps, 1, sl->qscale);

    // FIXME qscale / qp ... stuff

    if (sl->slice_type == AV_PICTURE_TYPE_SP)

        get_bits1(&sl->gb); /* sp_for_switch_flag */

    if (sl->slice_type == AV_PICTURE_TYPE_SP ||

        sl->slice_type == AV_PICTURE_TYPE_SI)

        get_se_golomb(&sl->gb); /* slice_qs_delta */



    sl->deblocking_filter     = 1;

    sl->slice_alpha_c0_offset = 0;

    sl->slice_beta_offset     = 0;

    if (pps->deblocking_filter_parameters_present) {

        tmp = get_ue_golomb_31(&sl->gb);

        if (tmp > 2) {

            av_log(h->avctx, AV_LOG_ERROR,

                   "deblocking_filter_idc %u out of range\n", tmp);

            return AVERROR_INVALIDDATA;

        }

        sl->deblocking_filter = tmp;

        if (sl->deblocking_filter < 2)

            sl->deblocking_filter ^= 1;  // 1<->0



        if (sl->deblocking_filter) {

            sl->slice_alpha_c0_offset = get_se_golomb(&sl->gb) * 2;

            sl->slice_beta_offset     = get_se_golomb(&sl->gb) * 2;

            if (sl->slice_alpha_c0_offset >  12 ||

                sl->slice_alpha_c0_offset < -12 ||

                sl->slice_beta_offset >  12     ||

                sl->slice_beta_offset < -12) {

                av_log(h->avctx, AV_LOG_ERROR,

                       "deblocking filter parameters %d %d out of range\n",

                       sl->slice_alpha_c0_offset, sl->slice_beta_offset);

                return AVERROR_INVALIDDATA;

            }

        }

    }



    return 0;

}

```

### Demonstration

```c

static int h264_slice_header_parse(const H264Context *h, H264SliceContext *sl,

                                   const H2645NAL *nal)

{

    const SPS *sps;

    const PPS *pps;

    int ret;

    unsigned int slice_type, tmp, i;

    int field_pic_flag, bottom_field_flag;

    int droppable, picture_structure;



    sl->first_mb_addr = get_ue_golomb(&sl->gb);



    slice_type = get_ue_golomb_31(&sl->gb);

    if (slice_type > 9) {

        av_log(h->avctx, AV_LOG_ERROR,

               "slice type %d too large at %d\n",

               slice_type, sl->first_mb_addr);

        return AVERROR_INVALIDDATA;

    }

    if (slice_type > 4) {

        slice_type -= 5;

        sl->slice_type_fixed = 1;

    } else

        sl->slice_type_fixed = 0;



    slice_type         = ff_h264_golomb_to_pict_type[slice_type];

    sl->slice_type     = slice_type;

    sl->slice_type_nos = slice_type & 3;



    if (nal->type  == NAL_IDR_SLICE &&

        sl->slice_type_nos != AV_PICTURE_TYPE_I) {

        av_log(h->avctx, AV_LOG_ERROR, "A non-intra slice in an IDR NAL unit.\n");

        return AVERROR_INVALIDDATA;

    }



    sl->pps_id = get_ue_golomb(&sl->gb);

    if (sl->pps_id >= MAX_PPS_COUNT) {

        av_log(h->avctx, AV_LOG_ERROR, "pps_id %u out of range\n", sl->pps_id);

        return AVERROR_INVALIDDATA;

    }

    if (!h->ps.pps_list[sl->pps_id]) {

        av_log(h->avctx, AV_LOG_ERROR,

               "non-existing PPS %u referenced\n",

               sl->pps_id);

        return AVERROR_INVALIDDATA;

    }

    pps = (const PPS*)h->ps.pps_list[sl->pps_id]->data;



    if (!h->ps.sps_list[pps->sps_id]) {

        av_log(h->avctx, AV_LOG_ERROR,

               "non-existing SPS %u referenced\n", pps->sps_id);

        return AVERROR_INVALIDDATA;

    }

    sps = (const SPS*)h->ps.sps_list[pps->sps_id]->data;



    sl->frame_num = get_bits(&sl->gb, sps->log2_max_frame_num);



    sl->mb_mbaff       = 0;



    droppable = nal->ref_idc == 0;

    if (sps->frame_mbs_only_flag) {

        picture_structure = PICT_FRAME;

    } else {

        field_pic_flag = get_bits1(&sl->gb);

        if (field_pic_flag) {

            bottom_field_flag = get_bits1(&sl->gb);

            picture_structure = PICT_TOP_FIELD + bottom_field_flag;

        } else {

            picture_structure = PICT_FRAME;

        }

    }

    sl->picture_structure      = picture_structure;

    sl->mb_field_decoding_flag = picture_structure != PICT_FRAME;



    if (picture_structure == PICT_FRAME) {

        sl->curr_pic_num = sl->frame_num;

        sl->max_pic_num  = 1 << sps->log2_max_frame_num;

    } else {

        sl->curr_pic_num = 2 * sl->frame_num + 1;

        sl->max_pic_num  = 1 << (sps->log2_max_frame_num + 1);

    }



    if (nal->type == NAL_IDR_SLICE)

        get_ue_golomb(&sl->gb); /* idr_pic_id */



    if (sps->poc_type == 0) {

        sl->poc_lsb = get_bits(&sl->gb, sps->log2_max_poc_lsb);



        if (pps->pic_order_present == 1 && picture_structure == PICT_FRAME)

            sl->delta_poc_bottom = get_se_golomb(&sl->gb);

    }



    if (sps->poc_type == 1 && !sps->delta_pic_order_always_zero_flag) {

        sl->delta_poc[0] = get_se_golomb(&sl->gb);



        if (pps->pic_order_present == 1 && picture_structure == PICT_FRAME)

            sl->delta_poc[1] = get_se_golomb(&sl->gb);

    }



    if (pps->redundant_pic_cnt_present)

        sl->redundant_pic_count = get_ue_golomb(&sl->gb);



    if (sl->slice_type_nos == AV_PICTURE_TYPE_B)

        sl->direct_spatial_mv_pred = get_bits1(&sl->gb);



    ret = ff_h264_parse_ref_count(&sl->list_count, sl->ref_count,

                                  &sl->gb, pps, sl->slice_type_nos,

                                  picture_structure);

    if (ret < 0)

        return ret;



    if (sl->slice_type_nos != AV_PICTURE_TYPE_I) {

       ret = ff_h264_decode_ref_pic_list_reordering(h, sl);

       if (ret < 0) {

           sl->ref_count[1] = sl->ref_count[0] = 0;

           return ret;

       }

    }



    sl->pwt.use_weight = 0;

    for (i = 0; i < 2; i++) {

        sl->pwt.luma_weight_flag[i]   = 0;

        sl->pwt.chroma_weight_flag[i] = 0;

    }

    if ((pps->weighted_pred && sl->slice_type_nos == AV_PICTURE_TYPE_P) ||

        (pps->weighted_bipred_idc == 1 &&

         sl->slice_type_nos == AV_PICTURE_TYPE_B))

        ff_h264_pred_weight_table(&sl->gb, sps, sl->ref_count,

                                  sl->slice_type_nos, &sl->pwt);



    sl->explicit_ref_marking = 0;

    if (nal->ref_idc) {

        ret = ff_h264_decode_ref_pic_marking(h, sl, &sl->gb);

        if (ret < 0 && (h->avctx->err_recognition & AV_EF_EXPLODE))

            return AVERROR_INVALIDDATA;

    }



    if (sl->slice_type_nos != AV_PICTURE_TYPE_I && pps->cabac) {

        tmp = get_ue_golomb_31(&sl->gb);

        if (tmp > 2) {

            av_log(h->avctx, AV_LOG_ERROR, "cabac_init_idc %u overflow\n", tmp);

            return AVERROR_INVALIDDATA;

        }

        sl->cabac_init_idc = tmp;

    }



    sl->last_qscale_diff = 0;

    tmp = pps->init_qp + get_se_golomb(&sl->gb);

    if (tmp > 51 + 6 * (sps->bit_depth_luma - 8)) {

        av_log(h->avctx, AV_LOG_ERROR, "QP %u out of range\n", tmp);

        return AVERROR_INVALIDDATA;

    }

    sl->qscale       = tmp;

    sl->chroma_qp[0] = get_chroma_qp(pps, 0, sl->qscale);

    sl->chroma_qp[1] = get_chroma_qp(pps, 1, sl->qscale);

    // FIXME qscale / qp ... stuff

    if (sl->slice_type == AV_PICTURE_TYPE_SP)

        get_bits1(&sl->gb); /* sp_for_switch_flag */

    if (sl->slice_type == AV_PICTURE_TYPE_SP ||

        sl->slice_type == AV_PICTURE_TYPE_SI)

        get_se_golomb(&sl->gb); /* slice_qs_delta */



    sl->deblocking_filter     = 1;

    sl->slice_alpha_c0_offset = 0;

    sl->slice_beta_offset     = 0;

    if (pps->deblocking_filter_parameters_present) {

        tmp = get_ue_golomb_31(&sl->gb);

        if (tmp > 2) {

            av_log(h->avctx, AV_LOG_ERROR,

                   "deblocking_filter_idc %u out of range\n", tmp);

            return AVERROR_INVALIDDATA;

        }

        sl->deblocking_filter = tmp;

        if (sl->deblocking_filter < 2)

            sl->deblocking_filter ^= 1;  // 1<->0



        if (sl->deblocking_filter) {

            sl->slice_alpha_c0_offset = get_se_golomb(&sl->gb) * 2;

            sl->slice_beta_offset     = get_se_golomb(&sl->gb) * 2;

            if (sl->slice_alpha_c0_offset >  12 ||

                sl->slice_alpha_c0_offset < -12 ||

                sl->slice_beta_offset >  12     ||

                sl->slice_beta_offset < -12) {

                av_log(h->avctx, AV_LOG_ERROR,

                       "deblocking filter parameters %d %d out of range\n",

                       sl->slice_alpha_c0_offset, sl->slice_beta_offset);

                return AVERROR_INVALIDDATA;

            }

        }

    }



    return 0;

}

```

## H2R-034

### Query

```c

struct vhost_net *vhost_net_init(VLANClientState *backend, int devfd,

                                 bool force)

{


    return NULL;

}

```

### Demonstration

```c

bool vhost_net_query(VHostNetState *net, VirtIODevice *dev)

{

    return false;

}

```

## H2R-035

### Query

```c

static av_cold int ffv1_encode_init(AVCodecContext *avctx)

{

    FFV1Context *s = avctx->priv_data;

    const AVPixFmtDescriptor *desc = av_pix_fmt_desc_get(avctx->pix_fmt);

    int i, j, k, m, ret;



    ffv1_common_init(avctx);



    s->version = 0;



    if ((avctx->flags & (CODEC_FLAG_PASS1 | CODEC_FLAG_PASS2)) ||

        avctx->slices > 1)

        s->version = FFMAX(s->version, 2);



    if (avctx->level == 3) {

        s->version = 3;

    }



    if (s->ec < 0) {

        s->ec = (s->version >= 3);

    }



    if (s->version >= 2 &&

        avctx->strict_std_compliance > FF_COMPLIANCE_EXPERIMENTAL) {

        av_log(avctx, AV_LOG_ERROR,

               "Version %d requested, please set -strict experimental in "

               "order to enable it\n",

               s->version);

        return AVERROR(ENOSYS);

    }



    s->ac = avctx->coder_type > 0 ? 2 : 0;



    s->plane_count = 3;

    switch (avctx->pix_fmt) {

    case AV_PIX_FMT_YUV444P9:

    case AV_PIX_FMT_YUV422P9:

    case AV_PIX_FMT_YUV420P9:

        if (!avctx->bits_per_raw_sample)

            s->bits_per_raw_sample = 9;

    case AV_PIX_FMT_YUV444P10:

    case AV_PIX_FMT_YUV420P10:

    case AV_PIX_FMT_YUV422P10:

        s->packed_at_lsb = 1;

        if (!avctx->bits_per_raw_sample && !s->bits_per_raw_sample)

            s->bits_per_raw_sample = 10;

    case AV_PIX_FMT_GRAY16:

    case AV_PIX_FMT_YUV444P16:

    case AV_PIX_FMT_YUV422P16:

    case AV_PIX_FMT_YUV420P16:

        if (!avctx->bits_per_raw_sample && !s->bits_per_raw_sample) {

            s->bits_per_raw_sample = 16;

        } else if (!s->bits_per_raw_sample) {

            s->bits_per_raw_sample = avctx->bits_per_raw_sample;

        }

        if (s->bits_per_raw_sample <= 8) {

            av_log(avctx, AV_LOG_ERROR, "bits_per_raw_sample invalid\n");

            return AVERROR_INVALIDDATA;

        }

        if (!s->ac && avctx->coder_type == -1) {

            av_log(avctx, AV_LOG_INFO,

                   "bits_per_raw_sample > 8, forcing coder 1\n");

            s->ac = 2;

        }

        if (!s->ac) {

            av_log(

                avctx, AV_LOG_ERROR,

                "bits_per_raw_sample of more than 8 needs -coder 1 currently\n");

            return AVERROR_INVALIDDATA;

        }

        s->version = FFMAX(s->version, 1);

    case AV_PIX_FMT_GRAY8:

    case AV_PIX_FMT_YUV444P:

    case AV_PIX_FMT_YUV440P:

    case AV_PIX_FMT_YUV422P:

    case AV_PIX_FMT_YUV420P:

    case AV_PIX_FMT_YUV411P:

    case AV_PIX_FMT_YUV410P:

        s->chroma_planes = desc->nb_components < 3 ? 0 : 1;

        s->colorspace    = 0;

        break;

    case AV_PIX_FMT_YUVA444P:

    case AV_PIX_FMT_YUVA422P:

    case AV_PIX_FMT_YUVA420P:

        s->chroma_planes = 1;

        s->colorspace    = 0;

        s->transparency  = 1;

        break;

    case AV_PIX_FMT_RGB32:

        s->colorspace   = 1;

        s->transparency = 1;

        break;

    case AV_PIX_FMT_GBRP9:

        if (!avctx->bits_per_raw_sample)

            s->bits_per_raw_sample = 9;

    case AV_PIX_FMT_GBRP10:

        if (!avctx->bits_per_raw_sample && !s->bits_per_raw_sample)

            s->bits_per_raw_sample = 10;

    case AV_PIX_FMT_GBRP16:

        if (!avctx->bits_per_raw_sample && !s->bits_per_raw_sample)

            s->bits_per_raw_sample = 16;

        else if (!s->bits_per_raw_sample)

            s->bits_per_raw_sample = avctx->bits_per_raw_sample;

        s->colorspace    = 1;

        s->chroma_planes = 1;

        s->version       = FFMAX(s->version, 1);

        break;

    default:

        av_log(avctx, AV_LOG_ERROR, "format not supported\n");

        return AVERROR_INVALIDDATA;

    }

    if (s->transparency) {

        av_log(

            avctx, AV_LOG_WARNING,

            "Storing alpha plane, this will require a recent FFV1 decoder to playback!\n");

    }

    if (avctx->context_model > 1U) {

        av_log(avctx, AV_LOG_ERROR,

               "Invalid context model %d, valid values are 0 and 1\n",

               avctx->context_model);

        return AVERROR(EINVAL);

    }



    if (s->ac > 1)

        for (i = 1; i < 256; i++)

            s->state_transition[i] = ffv1_ver2_state[i];



    for (i = 0; i < 256; i++) {

        s->quant_table_count = 2;

        if (s->bits_per_raw_sample <= 8) {

            s->quant_tables[0][0][i] = ffv1_quant11[i];

            s->quant_tables[0][1][i] = ffv1_quant11[i] * 11;

            s->quant_tables[0][2][i] = ffv1_quant11[i] * 11 * 11;

            s->quant_tables[1][0][i] = ffv1_quant11[i];

            s->quant_tables[1][1][i] = ffv1_quant11[i] * 11;

            s->quant_tables[1][2][i] = ffv1_quant5[i]  * 11 * 11;

            s->quant_tables[1][3][i] = ffv1_quant5[i]  *  5 * 11 * 11;

            s->quant_tables[1][4][i] = ffv1_quant5[i]  *  5 *  5 * 11 * 11;

        } else {

            s->quant_tables[0][0][i] = ffv1_quant9_10bit[i];

            s->quant_tables[0][1][i] = ffv1_quant9_10bit[i] * 11;

            s->quant_tables[0][2][i] = ffv1_quant9_10bit[i] * 11 * 11;

            s->quant_tables[1][0][i] = ffv1_quant9_10bit[i];

            s->quant_tables[1][1][i] = ffv1_quant9_10bit[i] * 11;

            s->quant_tables[1][2][i] = ffv1_quant5_10bit[i] * 11 * 11;

            s->quant_tables[1][3][i] = ffv1_quant5_10bit[i] *  5 * 11 * 11;

            s->quant_tables[1][4][i] = ffv1_quant5_10bit[i] *  5 *  5 * 11 * 11;

        }

    }

    s->context_count[0] = (11 * 11 * 11        + 1) / 2;

    s->context_count[1] = (11 * 11 * 5 * 5 * 5 + 1) / 2;

    memcpy(s->quant_table, s->quant_tables[avctx->context_model],

           sizeof(s->quant_table));



    for (i = 0; i < s->plane_count; i++) {

        PlaneContext *const p = &s->plane[i];



        memcpy(p->quant_table, s->quant_table, sizeof(p->quant_table));

        p->quant_table_index = avctx->context_model;

        p->context_count     = s->context_count[p->quant_table_index];

    }



    if ((ret = ffv1_allocate_initial_states(s)) < 0)

        return ret;



    avctx->coded_frame = av_frame_alloc();

    if (!avctx->coded_frame)

        return AVERROR(ENOMEM);



    avctx->coded_frame->pict_type = AV_PICTURE_TYPE_I;



    if (!s->transparency)

        s->plane_count = 2;



    av_pix_fmt_get_chroma_sub_sample(avctx->pix_fmt, &s->chroma_h_shift,

                                     &s->chroma_v_shift);



    s->picture_number = 0;



    if (avctx->flags & (CODEC_FLAG_PASS1 | CODEC_FLAG_PASS2)) {

        for (i = 0; i < s->quant_table_count; i++) {

            s->rc_stat2[i] = av_mallocz(s->context_count[i] *

                                        sizeof(*s->rc_stat2[i]));

            if (!s->rc_stat2[i])

                return AVERROR(ENOMEM);

        }

    }

    if (avctx->stats_in) {

        char *p = avctx->stats_in;

        uint8_t best_state[256][256];

        int gob_count = 0;

        char *next;



        av_assert0(s->version >= 2);



        for (;; ) {

            for (j = 0; j < 256; j++)

                for (i = 0; i < 2; i++) {

                    s->rc_stat[j][i] = strtol(p, &next, 0);

                    if (next == p) {

                        av_log(avctx, AV_LOG_ERROR,

                               "2Pass file invalid at %d %d [%s]\n", j, i, p);

                        return AVERROR_INVALIDDATA;

                    }

                    p = next;

                }

            for (i = 0; i < s->quant_table_count; i++)

                for (j = 0; j < s->context_count[i]; j++) {

                    for (k = 0; k < 32; k++)

                        for (m = 0; m < 2; m++) {

                            s->rc_stat2[i][j][k][m] = strtol(p, &next, 0);

                            if (next == p) {

                                av_log(avctx, AV_LOG_ERROR,

                                       "2Pass file invalid at %d %d %d %d [%s]\n",

                                       i, j, k, m, p);

                                return AVERROR_INVALIDDATA;

                            }

                            p = next;

                        }

                }

            gob_count = strtol(p, &next, 0);

            if (next == p || gob_count <= 0) {

                av_log(avctx, AV_LOG_ERROR, "2Pass file invalid\n");

                return AVERROR_INVALIDDATA;

            }

            p = next;

            while (*p == '\n' || *p == ' ')

                p++;

            if (p[0] == 0)

                break;

        }

        sort_stt(s, s->state_transition);



        find_best_state(best_state, s->state_transition);



        for (i = 0; i < s->quant_table_count; i++) {

            for (j = 0; j < s->context_count[i]; j++)

                for (k = 0; k < 32; k++) {

                    double p = 128;

                    if (s->rc_stat2[i][j][k][0] + s->rc_stat2[i][j][k][1]) {

                        p = 256.0 * s->rc_stat2[i][j][k][1] /

                            (s->rc_stat2[i][j][k][0] + s->rc_stat2[i][j][k][1]);

                    }

                    s->initial_states[i][j][k] =

                        best_state[av_clip(round(p), 1, 255)][av_clip((s->rc_stat2[i][j][k][0] +

                                                                       s->rc_stat2[i][j][k][1]) /

                                                                      gob_count, 0, 255)];

                }

        }

    }



    if (s->version > 1) {

        for (s->num_v_slices = 2; s->num_v_slices < 9; s->num_v_slices++)

            for (s->num_h_slices = s->num_v_slices;

                 s->num_h_slices < 2 * s->num_v_slices; s->num_h_slices++)

                if (avctx->slices == s->num_h_slices * s->num_v_slices &&

                    avctx->slices <= 64 || !avctx->slices)

                    goto slices_ok;

        av_log(avctx, AV_LOG_ERROR,

               "Unsupported number %d of slices requested, please specify a "

               "supported number with -slices (ex:4,6,9,12,16, ...)\n",

               avctx->slices);

        return AVERROR(ENOSYS);

slices_ok:

        write_extradata(s);

    }



    if ((ret = ffv1_init_slice_contexts(s)) < 0)

        return ret;

    if ((ret = init_slices_state(s)) < 0)

        return ret;



#define STATS_OUT_SIZE 1024 * 1024 * 6

    if (avctx->flags & CODEC_FLAG_PASS1) {

        avctx->stats_out = av_mallocz(STATS_OUT_SIZE);

        for (i = 0; i < s->quant_table_count; i++)

            for (j = 0; j < s->slice_count; j++) {

                FFV1Context *sf = s->slice_context[j];

                av_assert0(!sf->rc_stat2[i]);

                sf->rc_stat2[i] = av_mallocz(s->context_count[i] *

                                             sizeof(*sf->rc_stat2[i]));

                if (!sf->rc_stat2[i])

                    return AVERROR(ENOMEM);

            }

    }



    return 0;

}

```

### Demonstration

```c

static av_cold int vc1_decode_init(AVCodecContext *avctx)

{

    VC1Context *v = avctx->priv_data;

    MpegEncContext *s = &v->s;

    GetBitContext gb;



    /* save the container output size for WMImage */

    v->output_width  = avctx->width;

    v->output_height = avctx->height;



    if (!avctx->extradata_size || !avctx->extradata)

        return -1;

    if (!(avctx->flags & AV_CODEC_FLAG_GRAY))

        avctx->pix_fmt = ff_get_format(avctx, avctx->codec->pix_fmts);

    else

        avctx->pix_fmt = AV_PIX_FMT_GRAY8;

    v->s.avctx = avctx;



    if (ff_vc1_init_common(v) < 0)

        return -1;

    ff_blockdsp_init(&s->bdsp, avctx);

    ff_h264chroma_init(&v->h264chroma, 8);

    ff_qpeldsp_init(&s->qdsp);



    if (avctx->codec_id == AV_CODEC_ID_WMV3 || avctx->codec_id == AV_CODEC_ID_WMV3IMAGE) {

        int count = 0;



        // looks like WMV3 has a sequence header stored in the extradata

        // advanced sequence header may be before the first frame

        // the last byte of the extradata is a version number, 1 for the

        // samples we can decode



        init_get_bits(&gb, avctx->extradata, avctx->extradata_size*8);



        if (ff_vc1_decode_sequence_header(avctx, v, &gb) < 0)

          return -1;



        count = avctx->extradata_size*8 - get_bits_count(&gb);

        if (count > 0) {

            av_log(avctx, AV_LOG_INFO, "Extra data: %i bits left, value: %X\n",

                   count, get_bits_long(&gb, FFMIN(count, 32)));

        } else if (count < 0) {

            av_log(avctx, AV_LOG_INFO, "Read %i bits in overflow\n", -count);

        }

    } else { // VC1/WVC1/WVP2

        const uint8_t *start = avctx->extradata;

        uint8_t *end = avctx->extradata + avctx->extradata_size;

        const uint8_t *next;

        int size, buf2_size;

        uint8_t *buf2 = NULL;

        int seq_initialized = 0, ep_initialized = 0;



        if (avctx->extradata_size < 16) {

            av_log(avctx, AV_LOG_ERROR, "Extradata size too small: %i\n", avctx->extradata_size);

            return -1;

        }



        buf2  = av_mallocz(avctx->extradata_size + AV_INPUT_BUFFER_PADDING_SIZE);

        start = find_next_marker(start, end); // in WVC1 extradata first byte is its size, but can be 0 in mkv

        next  = start;

        for (; next < end; start = next) {

            next = find_next_marker(start + 4, end);

            size = next - start - 4;

            if (size <= 0)

                continue;

            buf2_size = vc1_unescape_buffer(start + 4, size, buf2);

            init_get_bits(&gb, buf2, buf2_size * 8);

            switch (AV_RB32(start)) {

            case VC1_CODE_SEQHDR:

                if (ff_vc1_decode_sequence_header(avctx, v, &gb) < 0) {

                    av_free(buf2);

                    return -1;

                }

                seq_initialized = 1;

                break;

            case VC1_CODE_ENTRYPOINT:

                if (ff_vc1_decode_entry_point(avctx, v, &gb) < 0) {

                    av_free(buf2);

                    return -1;

                }

                ep_initialized = 1;

                break;

            }

        }

        av_free(buf2);

        if (!seq_initialized || !ep_initialized) {

            av_log(avctx, AV_LOG_ERROR, "Incomplete extradata\n");

            return -1;

        }

        v->res_sprite = (avctx->codec_id == AV_CODEC_ID_VC1IMAGE);

    }



    v->sprite_output_frame = av_frame_alloc();

    if (!v->sprite_output_frame)

        return AVERROR(ENOMEM);



    avctx->profile = v->profile;

    if (v->profile == PROFILE_ADVANCED)

        avctx->level = v->level;



    avctx->has_b_frames = !!avctx->max_b_frames;



    if (v->color_prim == 1 || v->color_prim == 5 || v->color_prim == 6)

        avctx->color_primaries = v->color_prim;

    if (v->transfer_char == 1 || v->transfer_char == 7)

        avctx->color_trc = v->transfer_char;

    if (v->matrix_coef == 1 || v->matrix_coef == 6 || v->matrix_coef == 7)

        avctx->colorspace = v->matrix_coef;



    s->mb_width  = (avctx->coded_width  + 15) >> 4;

    s->mb_height = (avctx->coded_height + 15) >> 4;



    if (v->profile == PROFILE_ADVANCED || v->res_fasttx) {

        ff_vc1_init_transposed_scantables(v);

    } else {

        memcpy(v->zz_8x8, ff_wmv1_scantable, 4*64);

        v->left_blk_sh = 3;

        v->top_blk_sh  = 0;

    }



    if (avctx->codec_id == AV_CODEC_ID_WMV3IMAGE || avctx->codec_id == AV_CODEC_ID_VC1IMAGE) {

        v->sprite_width  = avctx->coded_width;

        v->sprite_height = avctx->coded_height;



        avctx->coded_width  = avctx->width  = v->output_width;

        avctx->coded_height = avctx->height = v->output_height;



        // prevent 16.16 overflows

        if (v->sprite_width  > 1 << 14 ||

            v->sprite_height > 1 << 14 ||

            v->output_width  > 1 << 14 ||

            v->output_height > 1 << 14) return -1;

    }

    return 0;

}

```

## H2R-036

### Query

```c

static int cllc_decode_frame(AVCodecContext *avctx, void *data,
                             int *got_picture_ptr, AVPacket *avpkt)
{
    CLLCContext *ctx = avctx->priv_data;
    AVFrame *pic = data;
    ThreadFrame frame = { .f = data };
    uint8_t *src = avpkt->data;
    uint32_t info_tag, info_offset;
    int data_size;
    GetBitContext gb;
    int coding_type, ret;
    if (avpkt->size < 4 + 4) {
        av_log(avctx, AV_LOG_ERROR, "Frame is too small %d.\n", avpkt->size);
    }
    info_offset = 0;
    info_tag    = AV_RL32(src);
    if (info_tag == MKTAG('I', 'N', 'F', 'O')) {
        info_offset = AV_RL32(src + 4);
        if (info_offset > UINT32_MAX - 8 || info_offset + 8 > avpkt->size) {
            av_log(avctx, AV_LOG_ERROR,
                   "Invalid INFO header offset: 0x%08"PRIX32" is too large.\n",
                   info_offset);
        }
        ff_canopus_parse_info_tag(avctx, src + 8, info_offset);
        info_offset += 8;
        src         += info_offset;
    }
    data_size = (avpkt->size - info_offset) & ~1;
    /* Make sure our bswap16'd buffer is big enough */
    av_fast_padded_malloc(&ctx->swapped_buf,
                          &ctx->swapped_buf_size, data_size);
    if (!ctx->swapped_buf) {
        av_log(avctx, AV_LOG_ERROR, "Could not allocate swapped buffer.\n");
        return AVERROR(ENOMEM);
    }
    /* bswap16 the buffer since CLLC's bitreader works in 16-bit words */
    ctx->bdsp.bswap16_buf((uint16_t *) ctx->swapped_buf, (uint16_t *) src,
                          data_size / 2);
    if ((ret = init_get_bits8(&gb, ctx->swapped_buf, data_size)) < 0)
        return ret;
    /*
     * Read in coding type. The types are as follows:
     *
     * 0 - YUY2
     * 1 - BGR24 (Triples)
     * 2 - BGR24 (Quads)
     * 3 - BGRA
     */
    coding_type = (AV_RL32(src) >> 8) & 0xFF;
    av_log(avctx, AV_LOG_DEBUG, "Frame coding type: %d\n", coding_type);
    switch (coding_type) {
    case 0:
        avctx->pix_fmt             = AV_PIX_FMT_YUV422P;
        avctx->bits_per_raw_sample = 8;
        if ((ret = ff_thread_get_buffer(avctx, &frame, 0)) < 0)
            return ret;
        ret = decode_yuv_frame(ctx, &gb, pic);
        if (ret < 0)
            return ret;
        break;
    case 1:
    case 2:
        avctx->pix_fmt             = AV_PIX_FMT_RGB24;
        avctx->bits_per_raw_sample = 8;
        if ((ret = ff_thread_get_buffer(avctx, &frame, 0)) < 0)
            return ret;
        ret = decode_rgb24_frame(ctx, &gb, pic);
        if (ret < 0)
            return ret;
        break;
    case 3:
        avctx->pix_fmt             = AV_PIX_FMT_ARGB;
        avctx->bits_per_raw_sample = 8;
        if ((ret = ff_thread_get_buffer(avctx, &frame, 0)) < 0)
            return ret;
        ret = decode_argb_frame(ctx, &gb, pic);
        if (ret < 0)
            return ret;
        break;
    default:
        av_log(avctx, AV_LOG_ERROR, "Unknown coding type: %d.\n", coding_type);
    }
    pic->key_frame = 1;
    pic->pict_type = AV_PICTURE_TYPE_I;
    *got_picture_ptr = 1;
    return avpkt->size;
}

```

### Demonstration

```c

static int cllc_decode_frame(AVCodecContext *avctx, void *data,

                             int *got_picture_ptr, AVPacket *avpkt)

{

    CLLCContext *ctx = avctx->priv_data;

    AVFrame *pic = data;

    uint8_t *src = avpkt->data;

    uint32_t info_tag, info_offset;

    int data_size;

    GetBitContext gb;

    int coding_type, ret;



    /* Skip the INFO header if present */

    info_offset = 0;

    info_tag    = AV_RL32(src);

    if (info_tag == MKTAG('I', 'N', 'F', 'O')) {

        info_offset = AV_RL32(src + 4);

        if (info_offset > UINT32_MAX - 8 || info_offset + 8 > avpkt->size) {

            av_log(avctx, AV_LOG_ERROR,

                   "Invalid INFO header offset: 0x%08"PRIX32" is too large.\n",

                   info_offset);

            return AVERROR_INVALIDDATA;

        }



        info_offset += 8;

        src         += info_offset;



        av_log(avctx, AV_LOG_DEBUG, "Skipping INFO chunk.\n");

    }



    data_size = (avpkt->size - info_offset) & ~1;



    /* Make sure our bswap16'd buffer is big enough */

    av_fast_padded_malloc(&ctx->swapped_buf,

                          &ctx->swapped_buf_size, data_size);

    if (!ctx->swapped_buf) {

        av_log(avctx, AV_LOG_ERROR, "Could not allocate swapped buffer.\n");

        return AVERROR(ENOMEM);

    }



    /* bswap16 the buffer since CLLC's bitreader works in 16-bit words */

    ctx->bdsp.bswap16_buf((uint16_t *) ctx->swapped_buf, (uint16_t *) src,

                          data_size / 2);



    init_get_bits(&gb, ctx->swapped_buf, data_size * 8);



    /*

     * Read in coding type. The types are as follows:

     *

     * 0 - YUY2

     * 1 - BGR24 (Triples)

     * 2 - BGR24 (Quads)

     * 3 - BGRA

     */

    coding_type = (AV_RL32(src) >> 8) & 0xFF;

    av_log(avctx, AV_LOG_DEBUG, "Frame coding type: %d\n", coding_type);



    switch (coding_type) {

    case 0:

        avctx->pix_fmt             = AV_PIX_FMT_YUV422P;

        avctx->bits_per_raw_sample = 8;



        ret = ff_get_buffer(avctx, pic, 0);

        if (ret < 0) {

            av_log(avctx, AV_LOG_ERROR, "Could not allocate buffer.\n");

            return ret;

        }



        ret = decode_yuv_frame(ctx, &gb, pic);

        if (ret < 0)

            return ret;



        break;

    case 1:

    case 2:

        avctx->pix_fmt             = AV_PIX_FMT_RGB24;

        avctx->bits_per_raw_sample = 8;



        ret = ff_get_buffer(avctx, pic, 0);

        if (ret < 0) {

            av_log(avctx, AV_LOG_ERROR, "Could not allocate buffer.\n");

            return ret;

        }



        ret = decode_rgb24_frame(ctx, &gb, pic);

        if (ret < 0)

            return ret;



        break;

    case 3:

        avctx->pix_fmt             = AV_PIX_FMT_ARGB;

        avctx->bits_per_raw_sample = 8;



        ret = ff_get_buffer(avctx, pic, 0);

        if (ret < 0) {

            av_log(avctx, AV_LOG_ERROR, "Could not allocate buffer.\n");

            return ret;

        }



        ret = decode_argb_frame(ctx, &gb, pic);

        if (ret < 0)

            return ret;



        break;

    default:

        av_log(avctx, AV_LOG_ERROR, "Unknown coding type: %d.\n", coding_type);

        return AVERROR_INVALIDDATA;

    }



    pic->key_frame = 1;

    pic->pict_type = AV_PICTURE_TYPE_I;



    *got_picture_ptr = 1;



    return avpkt->size;

}

```

## H2R-037

### Query

```c

static int bdrv_rd_badreq_sectors(BlockDriverState *bs,

                                  int64_t sector_num, int nb_sectors)

{

    return

        nb_sectors < 0 ||

        sector_num < 0 ||

        nb_sectors > bs->total_sectors ||

        sector_num > bs->total_sectors - nb_sectors;

}

```

### Demonstration

```c

static int bdrv_wr_badreq_sectors(BlockDriverState *bs,

                                  int64_t sector_num, int nb_sectors)

{

    if (sector_num < 0 ||

        nb_sectors < 0)

        return 1;



    if (sector_num > bs->total_sectors - nb_sectors) {

        if (bs->autogrow)

            bs->total_sectors = sector_num + nb_sectors;

        else

            return 1;

    }

    return 0;

}

```

## H2R-038

### Query

```c

static int find_stream_index(AVFormatContext *s)

{

    int i;

    AVStream *st;



    if (s->nb_streams <= 0)

        return -1;

    for(i = 0; i < s->nb_streams; i++) {

        st = s->streams[i];

        if (st->codec.codec_type == CODEC_TYPE_VIDEO) {

            return i;

        }

    }

    return 0;

}

```

### Demonstration

```c

static int has_duration(AVFormatContext *ic)

{

    int i;

    AVStream *st;



    for(i = 0;i < ic->nb_streams; i++) {

        st = ic->streams[i];

        if (st->duration != AV_NOPTS_VALUE)

            return 1;

    }

    if (ic->duration)

        return 1;

    return 0;

}

```

## H2R-039

### Query

```c

static av_cold void free_frame_buffers(Indeo3DecodeContext *ctx)

{

    int p;



    ctx->width=

    ctx->height= 0;



    for (p = 0; p < 3; p++) {

        av_freep(&ctx->planes[p].buffers[0]);

        av_freep(&ctx->planes[p].buffers[1]);

        ctx->planes[p].pixels[0] = ctx->planes[p].pixels[1] = 0;

    }

}

```

### Demonstration

```c

static av_cold int g722_encode_close(AVCodecContext *avctx)

{

    G722Context *c = avctx->priv_data;

    int i;

    for (i = 0; i < 2; i++) {

        av_freep(&c->paths[i]);

        av_freep(&c->node_buf[i]);

        av_freep(&c->nodep_buf[i]);

    }

    return 0;

}

```

## H2R-040

### Query

```c

static void emulated_push_error(EmulatedState *card, uint64_t code)

{

    EmulEvent *event = (EmulEvent *)g_malloc(sizeof(EmulEvent));



    assert(event);

    event->p.error.type = EMUL_ERROR;

    event->p.error.code = code;

    emulated_push_event(card, event);

}

```

### Demonstration

```c

static void emulated_push_type(EmulatedState *card, uint32_t type)

{

    EmulEvent *event = (EmulEvent *)g_malloc(sizeof(EmulEvent));



    assert(event);

    event->p.gen.type = type;

    emulated_push_event(card, event);

}

```

## H2R-041

### Query

```c

static av_always_inline void decode_dc_coeffs(GetBitContext *gb, int16_t *out,

                                              int blocks_per_slice)

{

    int16_t prev_dc;

    int code, i, sign;



    OPEN_READER(re, gb);



    DECODE_CODEWORD(code, FIRST_DC_CB);

    prev_dc = TOSIGNED(code);

    out[0] = prev_dc;



    out += 64; // dc coeff for the next block



    code = 5;

    sign = 0;

    for (i = 1; i < blocks_per_slice; i++, out += 64) {

        DECODE_CODEWORD(code, dc_codebook[FFMIN(code, 6U)]);

        if(code) sign ^= -(code & 1);

        else     sign  = 0;

        prev_dc += (((code + 1) >> 1) ^ sign) - sign;

        out[0] = prev_dc;

    }

    CLOSE_READER(re, gb);

}

```

### Demonstration

```c

static av_always_inline void decode_dc_coeffs(GetBitContext *gb, DCTELEM *out,

                                              int blocks_per_slice)

{

    DCTELEM prev_dc;

    int code, i, sign;



    OPEN_READER(re, gb);



    DECODE_CODEWORD(code, FIRST_DC_CB);

    prev_dc = TOSIGNED(code);

    out[0] = prev_dc;



    out += 64; // dc coeff for the next block



    code = 5;

    sign = 0;

    for (i = 1; i < blocks_per_slice; i++, out += 64) {

        DECODE_CODEWORD(code, dc_codebook[FFMIN(code, 6)]);

        if(code) sign ^= -(code & 1);

        else     sign  = 0;

        prev_dc += (((code + 1) >> 1) ^ sign) - sign;

        out[0] = prev_dc;

    }

    CLOSE_READER(re, gb);

}

```

## H2R-042

### Query

```c

static inline int onenand_load_main(OneNANDState *s, int sec, int secn,

                void *dest)

{

    if (s->bdrv_cur)

        return bdrv_read(s->bdrv_cur, sec, dest, secn) < 0;

    else if (sec + secn > s->secs_cur)

        return 1;



    memcpy(dest, s->current + (sec << 9), secn << 9);



    return 0;

}

```

### Demonstration

```c

static inline int onenand_load_spare(OneNANDState *s, int sec, int secn,

                void *dest)

{

    uint8_t buf[512];



    if (s->blk_cur) {

        if (blk_read(s->blk_cur, s->secs_cur + (sec >> 5), buf, 1) < 0) {

            return 1;

        }

        memcpy(dest, buf + ((sec & 31) << 4), secn << 4);

    } else if (sec + secn > s->secs_cur) {

        return 1;

    } else {

        memcpy(dest, s->current + (s->secs_cur << 9) + (sec << 4), secn << 4);

    }

 

    return 0;

}

```

## H2R-043

### Query

```c

static void test_io_channel_setup_sync(SocketAddressLegacy *listen_addr,

                                       SocketAddressLegacy *connect_addr,

                                       QIOChannel **src,

                                       QIOChannel **dst)

{

    QIOChannelSocket *lioc;



    lioc = qio_channel_socket_new();

    qio_channel_socket_listen_sync(lioc, listen_addr, &error_abort);



    if (listen_addr->type == SOCKET_ADDRESS_LEGACY_KIND_INET) {

        SocketAddressLegacy *laddr = qio_channel_socket_get_local_address(

            lioc, &error_abort);



        g_free(connect_addr->u.inet.data->port);

        connect_addr->u.inet.data->port = g_strdup(laddr->u.inet.data->port);



        qapi_free_SocketAddressLegacy(laddr);

    }



    *src = QIO_CHANNEL(qio_channel_socket_new());

    qio_channel_socket_connect_sync(

        QIO_CHANNEL_SOCKET(*src), connect_addr, &error_abort);

    qio_channel_set_delay(*src, false);



    qio_channel_wait(QIO_CHANNEL(lioc), G_IO_IN);

    *dst = QIO_CHANNEL(qio_channel_socket_accept(lioc, &error_abort));

    g_assert(*dst);



    test_io_channel_set_socket_bufs(*src, *dst);



    object_unref(OBJECT(lioc));

}

```

### Demonstration

```c

static void test_io_channel_setup_sync(SocketAddress *listen_addr,

                                       SocketAddress *connect_addr,

                                       QIOChannel **src,

                                       QIOChannel **dst)

{

    QIOChannelSocket *lioc;



    lioc = qio_channel_socket_new();

    qio_channel_socket_listen_sync(lioc, listen_addr, &error_abort);



    if (listen_addr->type == SOCKET_ADDRESS_KIND_INET) {

        SocketAddress *laddr = qio_channel_socket_get_local_address(

            lioc, &error_abort);



        g_free(connect_addr->u.inet.data->port);

        connect_addr->u.inet.data->port = g_strdup(laddr->u.inet.data->port);



        qapi_free_SocketAddress(laddr);

    }



    *src = QIO_CHANNEL(qio_channel_socket_new());

    qio_channel_socket_connect_sync(

        QIO_CHANNEL_SOCKET(*src), connect_addr, &error_abort);

    qio_channel_set_delay(*src, false);



    qio_channel_wait(QIO_CHANNEL(lioc), G_IO_IN);

    *dst = QIO_CHANNEL(qio_channel_socket_accept(lioc, &error_abort));

    g_assert(*dst);



    test_io_channel_set_socket_bufs(*src, *dst);



    object_unref(OBJECT(lioc));

}

```

## H2R-044

### Query

```c

static void tricore_cpu_initfn(Object *obj)

{

    CPUState *cs = CPU(obj);

    TriCoreCPU *cpu = TRICORE_CPU(obj);

    CPUTriCoreState *env = &cpu->env;



    cs->env_ptr = env;

    cpu_exec_init(cs, &error_abort);



    if (tcg_enabled()) {

        tricore_tcg_init();

    }

}

```

### Demonstration

```c

static void mips_cpu_initfn(Object *obj)

{

    CPUState *cs = CPU(obj);

    MIPSCPU *cpu = MIPS_CPU(obj);

    CPUMIPSState *env = &cpu->env;



    cs->env_ptr = env;

    cpu_exec_init(cs, &error_abort);



    if (tcg_enabled()) {

        mips_tcg_init();

    }

}

```

## H2R-045

### Query

```c

void fw_cfg_add_callback(FWCfgState *s, uint16_t key, FWCfgCallback callback,

                         void *callback_opaque, uint8_t *data, size_t len)

{

    int arch = !!(key & FW_CFG_ARCH_LOCAL);



    assert(key & FW_CFG_WRITE_CHANNEL);



    key &= FW_CFG_ENTRY_MASK;



    assert(key < FW_CFG_MAX_ENTRY && len <= 65535);



    s->entries[arch][key].data = data;

    s->entries[arch][key].len = len;

    s->entries[arch][key].callback_opaque = callback_opaque;

    s->entries[arch][key].callback = callback;

}

```

### Demonstration

```c

void fw_cfg_add_bytes(FWCfgState *s, uint16_t key, uint8_t *data, uint32_t len)

{

    int arch = !!(key & FW_CFG_ARCH_LOCAL);



    key &= FW_CFG_ENTRY_MASK;



    assert(key < FW_CFG_MAX_ENTRY);



    s->entries[arch][key].data = data;

    s->entries[arch][key].len = len;

}

```

## H2R-046

### Query

```c

static int hevc_decode_frame(AVCodecContext *avctx, void *data, int *got_output,

                             AVPacket *avpkt)

{

    int ret;

    int new_extradata_size;

    uint8_t *new_extradata;

    HEVCContext *s = avctx->priv_data;



    if (!avpkt->size) {

        ret = ff_hevc_output_frame(s, data, 1);

        if (ret < 0)

            return ret;



        *got_output = ret;

        return 0;

    }



    new_extradata = av_packet_get_side_data(avpkt, AV_PKT_DATA_NEW_EXTRADATA,

                                            &new_extradata_size);

    if (new_extradata && new_extradata_size > 0) {

        ret = hevc_decode_extradata(s, new_extradata, new_extradata_size);

        if (ret < 0)

            return ret;

    }



    s->ref = NULL;

    ret    = decode_nal_units(s, avpkt->data, avpkt->size);

    if (ret < 0)

        return ret;



    if (avctx->hwaccel) {

        if (s->ref && (ret = avctx->hwaccel->end_frame(avctx)) < 0) {

            av_log(avctx, AV_LOG_ERROR,

                   "hardware accelerator failed to decode picture\n");

            ff_hevc_unref_frame(s, s->ref, ~0);

            return ret;

        }

    } else {

        /* verify the SEI checksum */

        if (avctx->err_recognition & AV_EF_CRCCHECK && s->is_decoded &&

            s->sei.picture_hash.is_md5) {

            ret = verify_md5(s, s->ref->frame);

            if (ret < 0 && avctx->err_recognition & AV_EF_EXPLODE) {

                ff_hevc_unref_frame(s, s->ref, ~0);

                return ret;

            }

        }

    }

    s->sei.picture_hash.is_md5 = 0;



    if (s->is_decoded) {

        av_log(avctx, AV_LOG_DEBUG, "Decoded frame with POC %d.\n", s->poc);

        s->is_decoded = 0;

    }



    if (s->output_frame->buf[0]) {

        av_frame_move_ref(data, s->output_frame);

        *got_output = 1;

    }



    return avpkt->size;

}

```

### Demonstration

```c

static int hevc_decode_frame(AVCodecContext *avctx, void *data, int *got_output,

                             AVPacket *avpkt)

{

    int ret;

    HEVCContext *s = avctx->priv_data;



    if (!avpkt->size) {

        ret = ff_hevc_output_frame(s, data, 1);

        if (ret < 0)

            return ret;



        *got_output = ret;

        return 0;

    }



    s->ref = NULL;

    ret    = decode_nal_units(s, avpkt->data, avpkt->size);

    if (ret < 0)

        return ret;



    /* verify the SEI checksum */

    if (avctx->err_recognition & AV_EF_CRCCHECK && s->is_decoded &&

        avctx->err_recognition & AV_EF_EXPLODE &&

        s->is_md5) {

        ret = verify_md5(s, s->ref->frame);

        if (ret < 0) {

            ff_hevc_unref_frame(s, s->ref, ~0);

            return ret;

        }

    }

    s->is_md5 = 0;



    if (s->is_decoded) {

        av_log(avctx, AV_LOG_DEBUG, "Decoded frame with POC %d.\n", s->poc);

        s->is_decoded = 0;

    }



    if (s->output_frame->buf[0]) {

        av_frame_move_ref(data, s->output_frame);

        *got_output = 1;

    }



    return avpkt->size;

}

```

## H2R-047

### Query

```c

static void cpu_ioreq_pio(ioreq_t *req)

{

    int i;



    if (req->dir == IOREQ_READ) {

        if (!req->data_is_ptr) {

            req->data = do_inp(req->addr, req->size);

        } else {

            uint32_t tmp;



            for (i = 0; i < req->count; i++) {

                tmp = do_inp(req->addr, req->size);

                write_phys_req_item(req->data, req, i, &tmp);

            }

        }

    } else if (req->dir == IOREQ_WRITE) {

        if (!req->data_is_ptr) {

            do_outp(req->addr, req->size, req->data);

        } else {

            for (i = 0; i < req->count; i++) {

                uint32_t tmp = 0;



                read_phys_req_item(req->data, req, i, &tmp);

                do_outp(req->addr, req->size, tmp);

            }

        }

    }

}

```

### Demonstration

```c

static void cpu_ioreq_move(ioreq_t *req)

{

    int i, sign;



    sign = req->df ? -1 : 1;



    if (!req->data_is_ptr) {

        if (req->dir == IOREQ_READ) {

            for (i = 0; i < req->count; i++) {

                cpu_physical_memory_read(

                        req->addr + (sign * i * (int64_t)req->size),

                        (uint8_t *) &req->data, req->size);

            }

        } else if (req->dir == IOREQ_WRITE) {

            for (i = 0; i < req->count; i++) {

                cpu_physical_memory_write(

                        req->addr + (sign * i * (int64_t)req->size),

                        (uint8_t *) &req->data, req->size);

            }

        }

    } else {

        uint64_t tmp;



        if (req->dir == IOREQ_READ) {

            for (i = 0; i < req->count; i++) {

                cpu_physical_memory_read(

                        req->addr + (sign * i * (int64_t)req->size),

                        (uint8_t*) &tmp, req->size);

                cpu_physical_memory_write(

                        req->data + (sign * i * (int64_t)req->size),

                        (uint8_t*) &tmp, req->size);

            }

        } else if (req->dir == IOREQ_WRITE) {

            for (i = 0; i < req->count; i++) {

                cpu_physical_memory_read(

                        req->data + (sign * i * (int64_t)req->size),

                        (uint8_t*) &tmp, req->size);

                cpu_physical_memory_write(

                        req->addr + (sign * i * (int64_t)req->size),

                        (uint8_t*) &tmp, req->size);

            }

        }

    }

}

```

## H2R-048

### Query

```c

static void rtas_ibm_change_msi(PowerPCCPU *cpu, sPAPRMachineState *spapr,

                                uint32_t token, uint32_t nargs,

                                target_ulong args, uint32_t nret,

                                target_ulong rets)

{

    uint32_t config_addr = rtas_ld(args, 0);

    uint64_t buid = rtas_ldq(args, 1);

    unsigned int func = rtas_ld(args, 3);

    unsigned int req_num = rtas_ld(args, 4); /* 0 == remove all */

    unsigned int seq_num = rtas_ld(args, 5);

    unsigned int ret_intr_type;

    unsigned int irq, max_irqs = 0, num = 0;

    sPAPRPHBState *phb = NULL;

    PCIDevice *pdev = NULL;

    spapr_pci_msi *msi;

    int *config_addr_key;



    switch (func) {

    case RTAS_CHANGE_MSI_FN:

    case RTAS_CHANGE_FN:

        ret_intr_type = RTAS_TYPE_MSI;

        break;

    case RTAS_CHANGE_MSIX_FN:

        ret_intr_type = RTAS_TYPE_MSIX;

        break;

    default:

        error_report("rtas_ibm_change_msi(%u) is not implemented", func);

        rtas_st(rets, 0, RTAS_OUT_PARAM_ERROR);

        return;

    }



    /* Fins sPAPRPHBState */

    phb = spapr_pci_find_phb(spapr, buid);

    if (phb) {

        pdev = spapr_pci_find_dev(spapr, buid, config_addr);

    }

    if (!phb || !pdev) {

        rtas_st(rets, 0, RTAS_OUT_PARAM_ERROR);

        return;

    }



    /* Releasing MSIs */

    if (!req_num) {

        msi = (spapr_pci_msi *) g_hash_table_lookup(phb->msi, &config_addr);

        if (!msi) {

            trace_spapr_pci_msi("Releasing wrong config", config_addr);

            rtas_st(rets, 0, RTAS_OUT_HW_ERROR);

            return;

        }



        xics_free(spapr->icp, msi->first_irq, msi->num);

        if (msi_present(pdev)) {

            spapr_msi_setmsg(pdev, 0, false, 0, num);

        }

        if (msix_present(pdev)) {

            spapr_msi_setmsg(pdev, 0, true, 0, num);

        }

        g_hash_table_remove(phb->msi, &config_addr);



        trace_spapr_pci_msi("Released MSIs", config_addr);

        rtas_st(rets, 0, RTAS_OUT_SUCCESS);

        rtas_st(rets, 1, 0);

        return;

    }



    /* Enabling MSI */



    /* Check if the device supports as many IRQs as requested */

    if (ret_intr_type == RTAS_TYPE_MSI) {

        max_irqs = msi_nr_vectors_allocated(pdev);

    } else if (ret_intr_type == RTAS_TYPE_MSIX) {

        max_irqs = pdev->msix_entries_nr;

    }

    if (!max_irqs) {

        error_report("Requested interrupt type %d is not enabled for device %x",

                     ret_intr_type, config_addr);

        rtas_st(rets, 0, -1); /* Hardware error */

        return;

    }

    /* Correct the number if the guest asked for too many */

    if (req_num > max_irqs) {

        trace_spapr_pci_msi_retry(config_addr, req_num, max_irqs);

        req_num = max_irqs;

        irq = 0; /* to avoid misleading trace */

        goto out;

    }



    /* Allocate MSIs */

    irq = xics_alloc_block(spapr->icp, 0, req_num, false,

                           ret_intr_type == RTAS_TYPE_MSI);

    if (!irq) {

        error_report("Cannot allocate MSIs for device %x", config_addr);

        rtas_st(rets, 0, RTAS_OUT_HW_ERROR);

        return;

    }



    /* Setup MSI/MSIX vectors in the device (via cfgspace or MSIX BAR) */

    spapr_msi_setmsg(pdev, SPAPR_PCI_MSI_WINDOW, ret_intr_type == RTAS_TYPE_MSIX,

                     irq, req_num);



    /* Add MSI device to cache */

    msi = g_new(spapr_pci_msi, 1);

    msi->first_irq = irq;

    msi->num = req_num;

    config_addr_key = g_new(int, 1);

    *config_addr_key = config_addr;

    g_hash_table_insert(phb->msi, config_addr_key, msi);



out:

    rtas_st(rets, 0, RTAS_OUT_SUCCESS);

    rtas_st(rets, 1, req_num);

    rtas_st(rets, 2, ++seq_num);

    if (nret > 3) {

        rtas_st(rets, 3, ret_intr_type);

    }



    trace_spapr_pci_rtas_ibm_change_msi(config_addr, func, req_num, irq);

}

```

### Demonstration

```c

static void rtas_ibm_change_msi(PowerPCCPU *cpu, sPAPRMachineState *spapr,

                                uint32_t token, uint32_t nargs,

                                target_ulong args, uint32_t nret,

                                target_ulong rets)

{

    uint32_t config_addr = rtas_ld(args, 0);

    uint64_t buid = rtas_ldq(args, 1);

    unsigned int func = rtas_ld(args, 3);

    unsigned int req_num = rtas_ld(args, 4); /* 0 == remove all */

    unsigned int seq_num = rtas_ld(args, 5);

    unsigned int ret_intr_type;

    unsigned int irq, max_irqs = 0;

    sPAPRPHBState *phb = NULL;

    PCIDevice *pdev = NULL;

    spapr_pci_msi *msi;

    int *config_addr_key;



    switch (func) {

    case RTAS_CHANGE_MSI_FN:

    case RTAS_CHANGE_FN:

        ret_intr_type = RTAS_TYPE_MSI;

        break;

    case RTAS_CHANGE_MSIX_FN:

        ret_intr_type = RTAS_TYPE_MSIX;

        break;

    default:

        error_report("rtas_ibm_change_msi(%u) is not implemented", func);

        rtas_st(rets, 0, RTAS_OUT_PARAM_ERROR);

        return;

    }



    /* Fins sPAPRPHBState */

    phb = spapr_pci_find_phb(spapr, buid);

    if (phb) {

        pdev = spapr_pci_find_dev(spapr, buid, config_addr);

    }

    if (!phb || !pdev) {

        rtas_st(rets, 0, RTAS_OUT_PARAM_ERROR);

        return;

    }



    /* Releasing MSIs */

    if (!req_num) {

        msi = (spapr_pci_msi *) g_hash_table_lookup(phb->msi, &config_addr);

        if (!msi) {

            trace_spapr_pci_msi("Releasing wrong config", config_addr);

            rtas_st(rets, 0, RTAS_OUT_HW_ERROR);

            return;

        }



        xics_free(spapr->icp, msi->first_irq, msi->num);

        if (msi_present(pdev)) {

            spapr_msi_setmsg(pdev, 0, false, 0, 0);

        }

        if (msix_present(pdev)) {

            spapr_msi_setmsg(pdev, 0, true, 0, 0);

        }

        g_hash_table_remove(phb->msi, &config_addr);



        trace_spapr_pci_msi("Released MSIs", config_addr);

        rtas_st(rets, 0, RTAS_OUT_SUCCESS);

        rtas_st(rets, 1, 0);

        return;

    }



    /* Enabling MSI */



    /* Check if the device supports as many IRQs as requested */

    if (ret_intr_type == RTAS_TYPE_MSI) {

        max_irqs = msi_nr_vectors_allocated(pdev);

    } else if (ret_intr_type == RTAS_TYPE_MSIX) {

        max_irqs = pdev->msix_entries_nr;

    }

    if (!max_irqs) {

        error_report("Requested interrupt type %d is not enabled for device %x",

                     ret_intr_type, config_addr);

        rtas_st(rets, 0, -1); /* Hardware error */

        return;

    }

    /* Correct the number if the guest asked for too many */

    if (req_num > max_irqs) {

        trace_spapr_pci_msi_retry(config_addr, req_num, max_irqs);

        req_num = max_irqs;

        irq = 0; /* to avoid misleading trace */

        goto out;

    }



    /* Allocate MSIs */

    irq = xics_alloc_block(spapr->icp, 0, req_num, false,

                           ret_intr_type == RTAS_TYPE_MSI);

    if (!irq) {

        error_report("Cannot allocate MSIs for device %x", config_addr);

        rtas_st(rets, 0, RTAS_OUT_HW_ERROR);

        return;

    }



    /* Setup MSI/MSIX vectors in the device (via cfgspace or MSIX BAR) */

    spapr_msi_setmsg(pdev, SPAPR_PCI_MSI_WINDOW, ret_intr_type == RTAS_TYPE_MSIX,

                     irq, req_num);



    /* Add MSI device to cache */

    msi = g_new(spapr_pci_msi, 1);

    msi->first_irq = irq;

    msi->num = req_num;

    config_addr_key = g_new(int, 1);

    *config_addr_key = config_addr;

    g_hash_table_insert(phb->msi, config_addr_key, msi);



out:

    rtas_st(rets, 0, RTAS_OUT_SUCCESS);

    rtas_st(rets, 1, req_num);

    rtas_st(rets, 2, ++seq_num);

    if (nret > 3) {

        rtas_st(rets, 3, ret_intr_type);

    }



    trace_spapr_pci_rtas_ibm_change_msi(config_addr, func, req_num, irq);

}

```

## H2R-049

### Query

```c

void ff_rtsp_undo_setup(AVFormatContext *s)

{

    RTSPState *rt = s->priv_data;

    int i;



    for (i = 0; i < rt->nb_rtsp_streams; i++) {

        RTSPStream *rtsp_st = rt->rtsp_streams[i];

        if (!rtsp_st)

            continue;

        if (rtsp_st->transport_priv) {

            if (s->oformat) {

                AVFormatContext *rtpctx = rtsp_st->transport_priv;

                av_write_trailer(rtpctx);

                if (rt->lower_transport == RTSP_LOWER_TRANSPORT_TCP) {

                    uint8_t *ptr;

                    url_close_dyn_buf(rtpctx->pb, &ptr);

                    av_free(ptr);

                } else {

                    url_fclose(rtpctx->pb);

                }

                av_metadata_free(&rtpctx->streams[0]->metadata);

                av_metadata_free(&rtpctx->metadata);


                av_free(rtpctx->streams[0]);

                av_free(rtpctx);

            } else if (rt->transport == RTSP_TRANSPORT_RDT && CONFIG_RTPDEC)

                ff_rdt_parse_close(rtsp_st->transport_priv);

            else if (CONFIG_RTPDEC)

                rtp_parse_close(rtsp_st->transport_priv);

        }

        rtsp_st->transport_priv = NULL;

        if (rtsp_st->rtp_handle)

            url_close(rtsp_st->rtp_handle);

        rtsp_st->rtp_handle = NULL;

    }

}

```

### Demonstration

```c

static int sap_write_close(AVFormatContext *s)

{

    struct SAPState *sap = s->priv_data;

    int i;



    for (i = 0; i < s->nb_streams; i++) {

        AVFormatContext *rtpctx = s->streams[i]->priv_data;

        if (!rtpctx)

            continue;

        av_write_trailer(rtpctx);

        url_fclose(rtpctx->pb);

        av_metadata_free(&rtpctx->streams[0]->metadata);

        av_metadata_free(&rtpctx->metadata);


        av_free(rtpctx->streams[0]);

        av_free(rtpctx);

        s->streams[i]->priv_data = NULL;

    }



    if (sap->last_time && sap->ann && sap->ann_fd) {

        sap->ann[0] |= 4; /* Session deletion*/

        url_write(sap->ann_fd, sap->ann, sap->ann_size);

    }



    av_freep(&sap->ann);

    if (sap->ann_fd)

        url_close(sap->ann_fd);

    ff_network_close();

    return 0;

}

```

## H2R-050

### Query

```c

void configure_alarms(char const *opt)

{

    int i;

    int cur = 0;

    int count = ARRAY_SIZE(alarm_timers) - 1;

    char *arg;

    char *name;

    struct qemu_alarm_timer tmp;



    if (!strcmp(opt, "?")) {

        show_available_alarms();

        exit(0);

    }



    arg = g_strdup(opt);



    /* Reorder the array */

    name = strtok(arg, ",");

    while (name) {

        for (i = 0; i < count && alarm_timers[i].name; i++) {

            if (!strcmp(alarm_timers[i].name, name))

                break;

        }



        if (i == count) {

            fprintf(stderr, "Unknown clock %s\n", name);

            goto next;

        }



        if (i < cur)

            /* Ignore */

            goto next;



	/* Swap */

        tmp = alarm_timers[i];

        alarm_timers[i] = alarm_timers[cur];

        alarm_timers[cur] = tmp;



        cur++;

next:

        name = strtok(NULL, ",");

    }



    g_free(arg);



    if (cur) {

        /* Disable remaining timers */

        for (i = cur; i < count; i++)

            alarm_timers[i].name = NULL;

    } else {

        show_available_alarms();

        exit(1);

    }

}

```

### Demonstration

```c

static void configure_alarms(char const *opt)

{

    int i;

    int cur = 0;

    int count = (sizeof(alarm_timers) / sizeof(*alarm_timers)) - 1;

    char *arg;

    char *name;



    if (!strcmp(opt, "help")) {

        show_available_alarms();

        exit(0);

    }



    arg = strdup(opt);



    /* Reorder the array */

    name = strtok(arg, ",");

    while (name) {

        struct qemu_alarm_timer tmp;



        for (i = 0; i < count; i++) {

            if (!strcmp(alarm_timers[i].name, name))

                break;

        }



        if (i == count) {

            fprintf(stderr, "Unknown clock %s\n", name);

            goto next;

        }



        if (i < cur)

            /* Ignore */

            goto next;



	/* Swap */

        tmp = alarm_timers[i];

        alarm_timers[i] = alarm_timers[cur];

        alarm_timers[cur] = tmp;



        cur++;

next:

        name = strtok(NULL, ",");

    }



    free(arg);



    if (cur) {

	/* Disable remaining timers */

        for (i = cur; i < count; i++)

            alarm_timers[i].name = NULL;

    }



    /* debug */

    show_available_alarms();

}

```

## H2R-051

### Query

```c

static void avc_luma_midh_qrt_and_aver_dst_8w_msa(const uint8_t *src,

                                                  int32_t src_stride,

                                                  uint8_t *dst,

                                                  int32_t dst_stride,

                                                  int32_t height,

                                                  uint8_t horiz_offset)

{

    uint32_t multiple8_cnt;



    for (multiple8_cnt = 2; multiple8_cnt--;) {

        avc_luma_midh_qrt_and_aver_dst_4w_msa(src, src_stride, dst, dst_stride,

                                              height, horiz_offset);



        src += 4;

        dst += 4;

    }

}

```

### Demonstration

```c

static void avc_luma_midh_qrt_and_aver_dst_16w_msa(const uint8_t *src,

                                                   int32_t src_stride,

                                                   uint8_t *dst,

                                                   int32_t dst_stride,

                                                   int32_t height,

                                                   uint8_t horiz_offset)

{

    uint32_t multiple8_cnt;



    for (multiple8_cnt = 4; multiple8_cnt--;) {

        avc_luma_midh_qrt_and_aver_dst_4w_msa(src, src_stride, dst, dst_stride,

                                              height, horiz_offset);



        src += 4;

        dst += 4;

    }

}

```

## H2R-052

### Query

```c

static int hls_write_header(AVFormatContext *s)

{

    HLSContext *hls = s->priv_data;

    int ret, i;

    char *p;

    const char *pattern = "%d.ts";

    int basename_size = strlen(s->filename) + strlen(pattern);



    hls->number      = 0;



    hls->recording_time = hls->time * 1000000;

    hls->start_pts      = AV_NOPTS_VALUE;



    for (i = 0; i < s->nb_streams; i++)

        hls->has_video +=

            s->streams[i]->codec->codec_type == AVMEDIA_TYPE_VIDEO;



    if (hls->has_video > 1)

        av_log(s, AV_LOG_WARNING,

               "More than a single video stream present, "

               "expect issues decoding it.\n");



    hls->oformat = av_guess_format("mpegts", NULL, NULL);



    if (!hls->oformat) {

        ret = AVERROR_MUXER_NOT_FOUND;

        goto fail;

    }



    hls->basename = av_malloc(basename_size);



    if (!hls->basename) {

        ret = AVERROR(ENOMEM);

        goto fail;

    }



    strcpy(hls->basename, s->filename);



    p = strrchr(hls->basename, '.');



    if (p)

        *p = '\0';



    av_strlcat(hls->basename, "%d.ts", basename_size);



    if ((ret = hls_mux_init(s)) < 0)

        goto fail;



    if ((ret = hls_start(s)) < 0)

        goto fail;



    if ((ret = avformat_write_header(hls->avf, NULL)) < 0)

        return ret;





fail:

    if (ret) {

        av_free(hls->basename);

        if (hls->avf)

            avformat_free_context(hls->avf);

    }

    return ret;

}

```

### Demonstration

```c

static int hls_write_header(AVFormatContext *s)

{

    HLSContext *hls = s->priv_data;

    int ret, i;

    char *p;

    const char *pattern = "%d.ts";

    const char *pattern_localtime_fmt = "-%s.ts";

    const char *vtt_pattern = "%d.vtt";

    AVDictionary *options = NULL;

    int basename_size;

    int vtt_basename_size;



    hls->sequence       = hls->start_sequence;

    hls->recording_time = (hls->init_time ? hls->init_time : hls->time) * AV_TIME_BASE;

    hls->start_pts      = AV_NOPTS_VALUE;



    if (hls->flags & HLS_PROGRAM_DATE_TIME) {

        time_t now0;

        time(&now0);

        hls->initial_prog_date_time = now0;

    }



    if (hls->format_options_str) {

        ret = av_dict_parse_string(&hls->format_options, hls->format_options_str, "=", ":", 0);

        if (ret < 0) {

            av_log(s, AV_LOG_ERROR, "Could not parse format options list '%s'\n", hls->format_options_str);

            goto fail;

        }

    }



    for (i = 0; i < s->nb_streams; i++) {

        hls->has_video +=

            s->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO;

        hls->has_subtitle +=

            s->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_SUBTITLE;

    }



    if (hls->has_video > 1)

        av_log(s, AV_LOG_WARNING,

               "More than a single video stream present, "

               "expect issues decoding it.\n");



    hls->oformat = av_guess_format("mpegts", NULL, NULL);



    if (!hls->oformat) {

        ret = AVERROR_MUXER_NOT_FOUND;

        goto fail;

    }



    if(hls->has_subtitle) {

        hls->vtt_oformat = av_guess_format("webvtt", NULL, NULL);

        if (!hls->oformat) {

            ret = AVERROR_MUXER_NOT_FOUND;

            goto fail;

        }

    }



    if (hls->segment_filename) {

        hls->basename = av_strdup(hls->segment_filename);

        if (!hls->basename) {

            ret = AVERROR(ENOMEM);

            goto fail;

        }

    } else {

        if (hls->flags & HLS_SINGLE_FILE)

            pattern = ".ts";



        if (hls->use_localtime) {

            basename_size = strlen(s->filename) + strlen(pattern_localtime_fmt) + 1;

        } else {

            basename_size = strlen(s->filename) + strlen(pattern) + 1;

        }

        hls->basename = av_malloc(basename_size);

        if (!hls->basename) {

            ret = AVERROR(ENOMEM);

            goto fail;

        }



        av_strlcpy(hls->basename, s->filename, basename_size);



        p = strrchr(hls->basename, '.');

        if (p)

            *p = '\0';

        if (hls->use_localtime) {

            av_strlcat(hls->basename, pattern_localtime_fmt, basename_size);

        } else {

            av_strlcat(hls->basename, pattern, basename_size);

        }

    }

    if (!hls->use_localtime && (hls->flags & HLS_SECOND_LEVEL_SEGMENT_INDEX)) {

        av_log(hls, AV_LOG_ERROR, "second_level_segment_index hls_flag requires use_localtime to be true\n");

        ret = AVERROR(EINVAL);

        goto fail;

    }

    if(hls->has_subtitle) {



        if (hls->flags & HLS_SINGLE_FILE)

            vtt_pattern = ".vtt";

        vtt_basename_size = strlen(s->filename) + strlen(vtt_pattern) + 1;

        hls->vtt_basename = av_malloc(vtt_basename_size);

        if (!hls->vtt_basename) {

            ret = AVERROR(ENOMEM);

            goto fail;

        }

        hls->vtt_m3u8_name = av_malloc(vtt_basename_size);

        if (!hls->vtt_m3u8_name ) {

            ret = AVERROR(ENOMEM);

            goto fail;

        }

        av_strlcpy(hls->vtt_basename, s->filename, vtt_basename_size);

        p = strrchr(hls->vtt_basename, '.');

        if (p)

            *p = '\0';



        if( hls->subtitle_filename ) {

            strcpy(hls->vtt_m3u8_name, hls->subtitle_filename);

        } else {

            strcpy(hls->vtt_m3u8_name, hls->vtt_basename);

            av_strlcat(hls->vtt_m3u8_name, "_vtt.m3u8", vtt_basename_size);

        }

        av_strlcat(hls->vtt_basename, vtt_pattern, vtt_basename_size);

    }



    if ((ret = hls_mux_init(s)) < 0)

        goto fail;



    if (hls->flags & HLS_APPEND_LIST) {

        parse_playlist(s, s->filename);

        hls->discontinuity = 1;

        if (hls->init_time > 0) {

            av_log(s, AV_LOG_WARNING, "append_list mode does not support hls_init_time,"

                   " hls_init_time value will have no effect\n");

            hls->init_time = 0;

            hls->recording_time = hls->time * AV_TIME_BASE;

        }

    }



    if ((ret = hls_start(s)) < 0)

        goto fail;



    av_dict_copy(&options, hls->format_options, 0);

    ret = avformat_write_header(hls->avf, &options);

    if (av_dict_count(options)) {

        av_log(s, AV_LOG_ERROR, "Some of provided format options in '%s' are not recognized\n", hls->format_options_str);

        ret = AVERROR(EINVAL);

        goto fail;

    }

    //av_assert0(s->nb_streams == hls->avf->nb_streams);

    for (i = 0; i < s->nb_streams; i++) {

        AVStream *inner_st;

        AVStream *outer_st = s->streams[i];



        if (hls->max_seg_size > 0) {

            if ((outer_st->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) &&

                (outer_st->codecpar->bit_rate > hls->max_seg_size)) {

                av_log(s, AV_LOG_WARNING, "Your video bitrate is bigger than hls_segment_size, "

                       "(%"PRId64 " > %"PRId64 "), the result maybe not be what you want.",

                       outer_st->codecpar->bit_rate, hls->max_seg_size);

            }

        }



        if (outer_st->codecpar->codec_type != AVMEDIA_TYPE_SUBTITLE)

            inner_st = hls->avf->streams[i];

        else if (hls->vtt_avf)

            inner_st = hls->vtt_avf->streams[0];

        else {

            /* We have a subtitle stream, when the user does not want one */

            inner_st = NULL;

            continue;

        }

        avpriv_set_pts_info(outer_st, inner_st->pts_wrap_bits, inner_st->time_base.num, inner_st->time_base.den);

    }

fail:



    av_dict_free(&options);

    if (ret < 0) {

        av_freep(&hls->basename);

        av_freep(&hls->vtt_basename);

        if (hls->avf)

            avformat_free_context(hls->avf);

        if (hls->vtt_avf)

            avformat_free_context(hls->vtt_avf);



    }

    return ret;

}

```

## H2R-053

### Query

```c

void ff_put_h264_qpel16_mc31_msa(uint8_t *dst, const uint8_t *src,

                                 ptrdiff_t stride)

{

    avc_luma_hv_qrt_16w_msa(src - 2,

                            src - (stride * 2) +

                            sizeof(uint8_t), stride, dst, stride, 16);

}

```

### Demonstration

```c

void ff_put_h264_qpel16_mc33_msa(uint8_t *dst, const uint8_t *src,

                                 ptrdiff_t stride)

{

    avc_luma_hv_qrt_16w_msa(src + stride - 2,

                            src - (stride * 2) +

                            sizeof(uint8_t), stride, dst, stride, 16);

}

```

## H2R-054

### Query

```c

static int xmv_read_header(AVFormatContext *s)

{

    XMVDemuxContext *xmv = s->priv_data;

    AVIOContext     *pb  = s->pb;



    uint32_t file_version;

    uint32_t this_packet_size;

    uint16_t audio_track;

    int ret;



    s->ctx_flags |= AVFMTCTX_NOHEADER;



    avio_skip(pb, 4); /* Next packet size */



    this_packet_size = avio_rl32(pb);



    avio_skip(pb, 4); /* Max packet size */

    avio_skip(pb, 4); /* "xobX" */



    file_version = avio_rl32(pb);

    if ((file_version != 4) && (file_version != 2))

        avpriv_request_sample(s, "Uncommon version %"PRIu32"", file_version);



    /* Video tracks */



    xmv->video_width    = avio_rl32(pb);

    xmv->video_height   = avio_rl32(pb);

    xmv->video_duration = avio_rl32(pb);



    /* Audio tracks */



    xmv->audio_track_count = avio_rl16(pb);



    avio_skip(pb, 2); /* Unknown (padding?) */



    xmv->audio = av_mallocz_array(xmv->audio_track_count, sizeof(XMVAudioPacket));

    if (!xmv->audio) {

        ret = AVERROR(ENOMEM);

        goto fail;

    }



    for (audio_track = 0; audio_track < xmv->audio_track_count; audio_track++) {

        XMVAudioPacket *packet = &xmv->audio[audio_track];



        packet->compression     = avio_rl16(pb);

        packet->channels        = avio_rl16(pb);

        packet->sample_rate     = avio_rl32(pb);

        packet->bits_per_sample = avio_rl16(pb);

        packet->flags           = avio_rl16(pb);



        packet->bit_rate      = packet->bits_per_sample *

                                packet->sample_rate *

                                packet->channels;

        packet->block_align   = XMV_BLOCK_ALIGN_SIZE * packet->channels;

        packet->block_samples = 64;

        packet->codec_id      = ff_wav_codec_get_id(packet->compression,

                                                    packet->bits_per_sample);



        packet->stream_index = -1;



        packet->frame_size  = 0;

        packet->block_count = 0;



        /* TODO: ADPCM'd 5.1 sound is encoded in three separate streams.

         *       Those need to be interleaved to a proper 5.1 stream. */

        if (packet->flags & XMV_AUDIO_ADPCM51)

            av_log(s, AV_LOG_WARNING, "Unsupported 5.1 ADPCM audio stream "

                                      "(0x%04X)\n", packet->flags);



        if (!packet->channels || !packet->sample_rate ||

             packet->channels >= UINT16_MAX / XMV_BLOCK_ALIGN_SIZE) {

            av_log(s, AV_LOG_ERROR, "Invalid parameters for audio track %"PRIu16".\n",

                   audio_track);

            ret = AVERROR_INVALIDDATA;

            goto fail;

        }

    }





    /* Initialize the packet context */



    xmv->next_packet_offset = avio_tell(pb);

    xmv->next_packet_size   = this_packet_size - xmv->next_packet_offset;

    xmv->stream_count       = xmv->audio_track_count + 1;



    return 0;



fail:

    xmv_read_close(s);

    return ret;

}

```

### Demonstration

```c

static int xmv_read_header(AVFormatContext *s)

{

    XMVDemuxContext *xmv = s->priv_data;

    AVIOContext     *pb  = s->pb;

    AVStream        *vst = NULL;



    uint32_t file_version;

    uint32_t this_packet_size;

    uint16_t audio_track;

    int ret;



    avio_skip(pb, 4); /* Next packet size */



    this_packet_size = avio_rl32(pb);



    avio_skip(pb, 4); /* Max packet size */

    avio_skip(pb, 4); /* "xobX" */



    file_version = avio_rl32(pb);

    if ((file_version != 4) && (file_version != 2))

        avpriv_request_sample(s, "Uncommon version %d", file_version);





    /* Video track */



    vst = avformat_new_stream(s, NULL);

    if (!vst)

        return AVERROR(ENOMEM);



    avpriv_set_pts_info(vst, 32, 1, 1000);



    vst->codec->codec_type = AVMEDIA_TYPE_VIDEO;

    vst->codec->codec_id   = AV_CODEC_ID_WMV2;

    vst->codec->codec_tag  = MKBETAG('W', 'M', 'V', '2');

    vst->codec->width      = avio_rl32(pb);

    vst->codec->height     = avio_rl32(pb);



    vst->duration          = avio_rl32(pb);



    xmv->video.stream_index = vst->index;



    /* Audio tracks */



    xmv->audio_track_count = avio_rl16(pb);



    avio_skip(pb, 2); /* Unknown (padding?) */



    xmv->audio_tracks = av_malloc(xmv->audio_track_count * sizeof(XMVAudioTrack));

    if (!xmv->audio_tracks)

        return AVERROR(ENOMEM);



    xmv->audio = av_malloc(xmv->audio_track_count * sizeof(XMVAudioPacket));

    if (!xmv->audio)

        return AVERROR(ENOMEM);



    for (audio_track = 0; audio_track < xmv->audio_track_count; audio_track++) {

        XMVAudioTrack  *track  = &xmv->audio_tracks[audio_track];

        XMVAudioPacket *packet = &xmv->audio       [audio_track];

        AVStream *ast = NULL;



        track->compression     = avio_rl16(pb);

        track->channels        = avio_rl16(pb);

        track->sample_rate     = avio_rl32(pb);

        track->bits_per_sample = avio_rl16(pb);

        track->flags           = avio_rl16(pb);



        track->bit_rate      = track->bits_per_sample *

                               track->sample_rate *

                               track->channels;

        track->block_align   = 36 * track->channels;

        track->block_samples = 64;

        track->codec_id      = ff_wav_codec_get_id(track->compression,

                                                   track->bits_per_sample);



        packet->track        = track;

        packet->stream_index = -1;



        packet->frame_size  = 0;

        packet->block_count = 0;



        /* TODO: ADPCM'd 5.1 sound is encoded in three separate streams.

         *       Those need to be interleaved to a proper 5.1 stream. */

        if (track->flags & XMV_AUDIO_ADPCM51)

            av_log(s, AV_LOG_WARNING, "Unsupported 5.1 ADPCM audio stream "

                                      "(0x%04X)\n", track->flags);



        if (!track->channels || !track->sample_rate) {

            av_log(s, AV_LOG_ERROR, "Invalid parameters for audio track %d.\n",

                   audio_track);

            ret = AVERROR_INVALIDDATA;

            goto fail;

        }



        ast = avformat_new_stream(s, NULL);

        if (!ast)

            return AVERROR(ENOMEM);



        ast->codec->codec_type            = AVMEDIA_TYPE_AUDIO;

        ast->codec->codec_id              = track->codec_id;

        ast->codec->codec_tag             = track->compression;

        ast->codec->channels              = track->channels;

        ast->codec->sample_rate           = track->sample_rate;

        ast->codec->bits_per_coded_sample = track->bits_per_sample;

        ast->codec->bit_rate              = track->bit_rate;

        ast->codec->block_align           = 36 * track->channels;



        avpriv_set_pts_info(ast, 32, track->block_samples, track->sample_rate);



        packet->stream_index = ast->index;



        ast->duration = vst->duration;

    }





    /** Initialize the packet context */



    xmv->next_packet_offset = avio_tell(pb);

    xmv->next_packet_size   = this_packet_size - xmv->next_packet_offset;

    xmv->stream_count       = xmv->audio_track_count + 1;



    return 0;



fail:

    xmv_read_close(s);

    return ret;

}

```

## H2R-055

### Query

```c

static int inet_connect_addr(struct addrinfo *addr, bool block,

                             bool *in_progress)

{

    int sock, rc;



    if (in_progress) {

        *in_progress = false;

    }



    sock = qemu_socket(addr->ai_family, addr->ai_socktype, addr->ai_protocol);

    if (sock < 0) {

        fprintf(stderr, "%s: socket(%s): %s\n", __func__,

                inet_strfamily(addr->ai_family), strerror(errno));

        return -1;

    }

    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on));

    if (!block) {

        socket_set_nonblock(sock);

    }

    /* connect to peer */

    do {

        rc = 0;

        if (connect(sock, addr->ai_addr, addr->ai_addrlen) < 0) {

            rc = -socket_error();

        }

    } while (rc == -EINTR);



    if (!block && QEMU_SOCKET_RC_INPROGRESS(rc)) {

        if (in_progress) {

            *in_progress = true;

        }

    } else if (rc < 0) {

        closesocket(sock);

        return -1;

    }

    return sock;

}

```

### Demonstration

```c

static int net_socket_mcast_create(struct sockaddr_in *mcastaddr, struct in_addr *localaddr)

{

    struct ip_mreq imr;

    int fd;

    int val, ret;

    if (!IN_MULTICAST(ntohl(mcastaddr->sin_addr.s_addr))) {

	fprintf(stderr, "qemu: error: specified mcastaddr \"%s\" (0x%08x) does not contain a multicast address\n",

		inet_ntoa(mcastaddr->sin_addr),

                (int)ntohl(mcastaddr->sin_addr.s_addr));

	return -1;



    }

    fd = qemu_socket(PF_INET, SOCK_DGRAM, 0);

    if (fd < 0) {

        perror("socket(PF_INET, SOCK_DGRAM)");

        return -1;

    }



    val = 1;

    ret=setsockopt(fd, SOL_SOCKET, SO_REUSEADDR,

                   (const char *)&val, sizeof(val));

    if (ret < 0) {

	perror("setsockopt(SOL_SOCKET, SO_REUSEADDR)");

	goto fail;

    }



    ret = bind(fd, (struct sockaddr *)mcastaddr, sizeof(*mcastaddr));

    if (ret < 0) {

        perror("bind");

        goto fail;

    }



    /* Add host to multicast group */

    imr.imr_multiaddr = mcastaddr->sin_addr;

    if (localaddr) {

        imr.imr_interface = *localaddr;

    } else {

        imr.imr_interface.s_addr = htonl(INADDR_ANY);

    }



    ret = setsockopt(fd, IPPROTO_IP, IP_ADD_MEMBERSHIP,

                     (const char *)&imr, sizeof(struct ip_mreq));

    if (ret < 0) {

	perror("setsockopt(IP_ADD_MEMBERSHIP)");

	goto fail;

    }



    /* Force mcast msgs to loopback (eg. several QEMUs in same host */

    val = 1;

    ret=setsockopt(fd, IPPROTO_IP, IP_MULTICAST_LOOP,

                   (const char *)&val, sizeof(val));

    if (ret < 0) {

	perror("setsockopt(SOL_IP, IP_MULTICAST_LOOP)");

	goto fail;

    }



    /* If a bind address is given, only send packets from that address */

    if (localaddr != NULL) {

        ret = setsockopt(fd, IPPROTO_IP, IP_MULTICAST_IF,

                         (const char *)localaddr, sizeof(*localaddr));

        if (ret < 0) {

            perror("setsockopt(IP_MULTICAST_IF)");

            goto fail;

        }

    }



    socket_set_nonblock(fd);

    return fd;

fail:

    if (fd >= 0)

        closesocket(fd);

    return -1;

}

```

## H2R-056

### Query

```c

static uint64_t omap_pwt_read(void *opaque, target_phys_addr_t addr,

                              unsigned size)

{

    struct omap_pwt_s *s = (struct omap_pwt_s *) opaque;

    int offset = addr & OMAP_MPUI_REG_MASK;



    if (size != 1) {

        return omap_badwidth_read8(opaque, addr);

    }



    switch (offset) {

    case 0x00:	/* FRC */

        return s->frc;

    case 0x04:	/* VCR */

        return s->vrc;

    case 0x08:	/* GCR */

        return s->gcr;

    }

    OMAP_BAD_REG(addr);

    return 0;

}

```

### Demonstration

```c

static uint64_t omap_pwl_read(void *opaque, target_phys_addr_t addr,

                              unsigned size)

{

    struct omap_pwl_s *s = (struct omap_pwl_s *) opaque;

    int offset = addr & OMAP_MPUI_REG_MASK;



    if (size != 1) {

        return omap_badwidth_read8(opaque, addr);

    }



    switch (offset) {

    case 0x00:	/* PWL_LEVEL */

        return s->level;

    case 0x04:	/* PWL_CTRL */

        return s->enable;

    }

    OMAP_BAD_REG(addr);

    return 0;

}

```

## H2R-057

### Query

```c

static void put_no_rnd_pixels_y2_mmx( UINT8  *block, const UINT8 *pixels, int line_size, int h)

{

  UINT8  *p;

  const UINT8 *pix;

  p = block;

  pix = pixels;

  MOVQ_ZERO(mm7);

  JUMPALIGN();

  do {

    __asm __volatile(

	"movq	%1, %%mm0\n\t"

	"movq	%2, %%mm1\n\t"

	"movq	%%mm0, %%mm2\n\t"

	"movq	%%mm1, %%mm3\n\t"

	"punpcklbw %%mm7, %%mm0\n\t"

	"punpcklbw %%mm7, %%mm1\n\t"

	"punpckhbw %%mm7, %%mm2\n\t"

	"punpckhbw %%mm7, %%mm3\n\t"

	"paddusw %%mm1, %%mm0\n\t"

	"paddusw %%mm3, %%mm2\n\t"

	"psrlw	$1, %%mm0\n\t"

	"psrlw	$1, %%mm2\n\t"

	"packuswb  %%mm2, %%mm0\n\t"

	"movq	%%mm0, %0\n\t"

	:"=m"(*p)

	:"m"(*pix),

	 "m"(*(pix+line_size))

	:"memory");

   pix += line_size;

   p +=   line_size;

  } while(--h);

}

```

### Demonstration

```c

static void   put_no_rnd_pixels_x2_mmx( UINT8  *block, const UINT8 *pixels, int line_size, int h)

{

  UINT8  *p;

  const UINT8 *pix;

  p = block;

  pix = pixels;

  MOVQ_ZERO(mm7);

  do {

    __asm __volatile(

	"movq	%1, %%mm0\n\t"

	"movq	1%1, %%mm1\n\t"

	"movq	%%mm0, %%mm2\n\t"

	"movq	%%mm1, %%mm3\n\t"

	"punpcklbw %%mm7, %%mm0\n\t"

	"punpcklbw %%mm7, %%mm1\n\t"

	"punpckhbw %%mm7, %%mm2\n\t"

	"punpckhbw %%mm7, %%mm3\n\t"

	"paddusw %%mm1, %%mm0\n\t"

	"paddusw %%mm3, %%mm2\n\t"

	"psrlw	$1, %%mm0\n\t"

	"psrlw	$1, %%mm2\n\t"

	"packuswb  %%mm2, %%mm0\n\t"

	"movq	%%mm0, %0\n\t"

	:"=m"(*p)

	:"m"(*pix)

	:"memory");

   pix += line_size;

   p +=   line_size;

  } while (--h);

}

```

## H2R-058

### Query

```c

bool error_is_type(Error *err, const char *fmt)

{

    const char *error_class;

    char *ptr;

    char *end;



    if (!err) {

        return false;

    }



    ptr = strstr(fmt, "'class': '");

    assert(ptr != NULL);

    ptr += strlen("'class': '");



    end = strchr(ptr, '\'');

    assert(end != NULL);



    error_class = error_get_field(err, "class");

    if (strlen(error_class) != end - ptr) {

        return false;

    }



    return strncmp(ptr, error_class, end - ptr) == 0;

}

```

### Demonstration

```c

static QDict *parse_json_filename(const char *filename, Error **errp)

{

    QObject *options_obj;

    QDict *options;

    int ret;



    ret = strstart(filename, "json:", &filename);

    assert(ret);



    options_obj = qobject_from_json(filename);

    if (!options_obj) {

        error_setg(errp, "Could not parse the JSON options");

        return NULL;

    }



    if (qobject_type(options_obj) != QTYPE_QDICT) {

        qobject_decref(options_obj);

        error_setg(errp, "Invalid JSON object given");

        return NULL;

    }



    options = qobject_to_qdict(options_obj);

    qdict_flatten(options);



    return options;

}

```

## H2R-059

### Query

```c

void avcodec_align_dimensions2(AVCodecContext *s, int *width, int *height, int linesize_align[4]){

    int w_align= 1;

    int h_align= 1;



    switch(s->pix_fmt){

    case PIX_FMT_YUV420P:

    case PIX_FMT_YUYV422:

    case PIX_FMT_UYVY422:

    case PIX_FMT_YUV422P:

    case PIX_FMT_YUV440P:

    case PIX_FMT_YUV444P:

    case PIX_FMT_GRAY8:

    case PIX_FMT_GRAY16BE:

    case PIX_FMT_GRAY16LE:

    case PIX_FMT_YUVJ420P:

    case PIX_FMT_YUVJ422P:

    case PIX_FMT_YUVJ440P:

    case PIX_FMT_YUVJ444P:

    case PIX_FMT_YUVA420P:

    case PIX_FMT_YUV420P9LE:

    case PIX_FMT_YUV420P9BE:

    case PIX_FMT_YUV420P10LE:

    case PIX_FMT_YUV420P10BE:

    case PIX_FMT_YUV422P10LE:

    case PIX_FMT_YUV422P10BE:





        w_align= 16; //FIXME check for non mpeg style codecs and use less alignment

        h_align= 16;

        if(s->codec_id == CODEC_ID_MPEG2VIDEO || s->codec_id == CODEC_ID_MJPEG || s->codec_id == CODEC_ID_AMV || s->codec_id == CODEC_ID_THP || s->codec_id == CODEC_ID_H264)

            h_align= 32; // interlaced is rounded up to 2 MBs

        break;

    case PIX_FMT_YUV411P:

    case PIX_FMT_UYYVYY411:

        w_align=32;

        h_align=8;

        break;

    case PIX_FMT_YUV410P:

        if(s->codec_id == CODEC_ID_SVQ1){

            w_align=64;

            h_align=64;

        }

    case PIX_FMT_RGB555:

        if(s->codec_id == CODEC_ID_RPZA){

            w_align=4;

            h_align=4;

        }

    case PIX_FMT_PAL8:

    case PIX_FMT_BGR8:

    case PIX_FMT_RGB8:

        if(s->codec_id == CODEC_ID_SMC){

            w_align=4;

            h_align=4;

        }

        break;

    case PIX_FMT_BGR24:

        if((s->codec_id == CODEC_ID_MSZH) || (s->codec_id == CODEC_ID_ZLIB)){

            w_align=4;

            h_align=4;

        }

        break;

    default:

        w_align= 1;

        h_align= 1;

        break;

    }



    *width = FFALIGN(*width , w_align);

    *height= FFALIGN(*height, h_align);

    if(s->codec_id == CODEC_ID_H264 || s->lowres)

        *height+=2; // some of the optimized chroma MC reads one line too much

                    // which is also done in mpeg decoders with lowres > 0



    linesize_align[0] =

    linesize_align[1] =

    linesize_align[2] =

    linesize_align[3] = STRIDE_ALIGN;

//STRIDE_ALIGN is 8 for SSE* but this does not work for SVQ1 chroma planes

//we could change STRIDE_ALIGN to 16 for x86/sse but it would increase the

//picture size unneccessarily in some cases. The solution here is not

//pretty and better ideas are welcome!

#if HAVE_MMX

    if(s->codec_id == CODEC_ID_SVQ1 || s->codec_id == CODEC_ID_VP5 ||

       s->codec_id == CODEC_ID_VP6 || s->codec_id == CODEC_ID_VP6F ||

       s->codec_id == CODEC_ID_VP6A) {

        linesize_align[0] =

        linesize_align[1] =

        linesize_align[2] = 16;

    }

#endif

}

```

### Demonstration

```c

void avcodec_align_dimensions2(AVCodecContext *s, int *width, int *height,

                               int linesize_align[AV_NUM_DATA_POINTERS])

{

    int i;

    int w_align= 1;

    int h_align= 1;



    switch(s->pix_fmt){

    case PIX_FMT_YUV420P:

    case PIX_FMT_YUYV422:

    case PIX_FMT_UYVY422:

    case PIX_FMT_YUV422P:

    case PIX_FMT_YUV440P:

    case PIX_FMT_YUV444P:

    case PIX_FMT_GBRP:

    case PIX_FMT_GRAY8:

    case PIX_FMT_GRAY16BE:

    case PIX_FMT_GRAY16LE:

    case PIX_FMT_YUVJ420P:

    case PIX_FMT_YUVJ422P:

    case PIX_FMT_YUVJ440P:

    case PIX_FMT_YUVJ444P:

    case PIX_FMT_YUVA420P:

    case PIX_FMT_YUV420P9LE:

    case PIX_FMT_YUV420P9BE:

    case PIX_FMT_YUV420P10LE:

    case PIX_FMT_YUV420P10BE:

    case PIX_FMT_YUV422P9LE:

    case PIX_FMT_YUV422P9BE:

    case PIX_FMT_YUV422P10LE:

    case PIX_FMT_YUV422P10BE:

    case PIX_FMT_YUV444P9LE:

    case PIX_FMT_YUV444P9BE:

    case PIX_FMT_YUV444P10LE:

    case PIX_FMT_YUV444P10BE:

    case PIX_FMT_GBRP9LE:

    case PIX_FMT_GBRP9BE:

    case PIX_FMT_GBRP10LE:

    case PIX_FMT_GBRP10BE:

        w_align = 16; //FIXME assume 16 pixel per macroblock

        h_align = 16 * 2; // interlaced needs 2 macroblocks height

        break;

    case PIX_FMT_YUV411P:

    case PIX_FMT_UYYVYY411:

        w_align=32;

        h_align=8;

        break;

    case PIX_FMT_YUV410P:

        if(s->codec_id == CODEC_ID_SVQ1){

            w_align=64;

            h_align=64;

        }

    case PIX_FMT_RGB555:

        if(s->codec_id == CODEC_ID_RPZA){

            w_align=4;

            h_align=4;

        }

    case PIX_FMT_PAL8:

    case PIX_FMT_BGR8:

    case PIX_FMT_RGB8:

        if(s->codec_id == CODEC_ID_SMC){

            w_align=4;

            h_align=4;

        }

        break;

    case PIX_FMT_BGR24:

        if((s->codec_id == CODEC_ID_MSZH) || (s->codec_id == CODEC_ID_ZLIB)){

            w_align=4;

            h_align=4;

        }

        break;

    default:

        w_align= 1;

        h_align= 1;

        break;

    }



    *width = FFALIGN(*width , w_align);

    *height= FFALIGN(*height, h_align);

    if(s->codec_id == CODEC_ID_H264 || s->lowres)

        *height+=2; // some of the optimized chroma MC reads one line too much

                    // which is also done in mpeg decoders with lowres > 0



    for (i = 0; i < AV_NUM_DATA_POINTERS; i++)

        linesize_align[i] = STRIDE_ALIGN;

//STRIDE_ALIGN is 8 for SSE* but this does not work for SVQ1 chroma planes

//we could change STRIDE_ALIGN to 16 for x86/sse but it would increase the

//picture size unneccessarily in some cases. The solution here is not

//pretty and better ideas are welcome!

#if HAVE_MMX

    if(s->codec_id == CODEC_ID_SVQ1 || s->codec_id == CODEC_ID_VP5 ||

       s->codec_id == CODEC_ID_VP6 || s->codec_id == CODEC_ID_VP6F ||

       s->codec_id == CODEC_ID_VP6A) {

        for (i = 0; i < AV_NUM_DATA_POINTERS; i++)

            linesize_align[i] = 16;

    }

#endif

}

```

## H2R-060

### Query

```c

void kqemu_set_notdirty(CPUState *env, ram_addr_t ram_addr)

{

    LOG_INT("kqemu_set_notdirty: addr=%08lx\n", 

                (unsigned long)ram_addr);

    /* we only track transitions to dirty state */

    if (phys_ram_dirty[ram_addr >> TARGET_PAGE_BITS] != 0xff)

        return;

    if (nb_ram_pages_to_update >= KQEMU_MAX_RAM_PAGES_TO_UPDATE)

        nb_ram_pages_to_update = KQEMU_RAM_PAGES_UPDATE_ALL;

    else

        ram_pages_to_update[nb_ram_pages_to_update++] = ram_addr;

}

```

### Demonstration

```c

void kqemu_flush_page(CPUState *env, target_ulong addr)

{

    LOG_INT("kqemu_flush_page: addr=" TARGET_FMT_lx "\n", addr);

    if (nb_pages_to_flush >= KQEMU_MAX_PAGES_TO_FLUSH)

        nb_pages_to_flush = KQEMU_FLUSH_ALL;

    else

        pages_to_flush[nb_pages_to_flush++] = addr;

}

```

## H2R-061

### Query

```c

static always_inline void gen_rldimi (DisasContext *ctx, int mbn, int shn)

{

    uint64_t mask;

    uint32_t sh, mb;



    sh = SH(ctx->opcode) | (shn << 5);

    mb = MB(ctx->opcode) | (mbn << 5);

    if (likely(sh == 0)) {

        if (likely(mb == 0)) {

            gen_op_load_gpr_T0(rS(ctx->opcode));

            goto do_store;

        } else if (likely(mb == 63)) {

            gen_op_load_gpr_T0(rA(ctx->opcode));

            goto do_store;

        }

        gen_op_load_gpr_T0(rS(ctx->opcode));

        gen_op_load_gpr_T1(rA(ctx->opcode));

        goto do_mask;

    }

    gen_op_load_gpr_T0(rS(ctx->opcode));

    gen_op_load_gpr_T1(rA(ctx->opcode));

    gen_op_rotli64_T0(sh);

 do_mask:

    mask = MASK(mb, 63 - sh);

    gen_andi_T0_64(ctx, mask);

    gen_andi_T1_64(ctx, ~mask);

    gen_op_or();

 do_store:

    gen_op_store_T0_gpr(rA(ctx->opcode));

    if (unlikely(Rc(ctx->opcode) != 0))

        gen_set_Rc0(ctx);

}

```

### Demonstration

```c

static always_inline void gen_op_neg (DisasContext *ctx, TCGv ret, TCGv arg1, int ov_check)

{

    int l1, l2;



    l1 = gen_new_label();

    l2 = gen_new_label();

#if defined(TARGET_PPC64)

    if (ctx->sf_mode) {

        tcg_gen_brcondi_tl(TCG_COND_EQ, arg1, INT64_MIN, l1);

    } else {

        TCGv t0 = tcg_temp_new(TCG_TYPE_TL);

	tcg_gen_ext32s_tl(t0, arg1);

        tcg_gen_brcondi_tl(TCG_COND_EQ, t0, INT32_MIN, l1);

    }

#else

        tcg_gen_brcondi_tl(TCG_COND_EQ, arg1, INT32_MIN, l1);

#endif

    tcg_gen_neg_tl(ret, arg1);

    if (ov_check) {

        tcg_gen_andi_tl(cpu_xer, cpu_xer, ~(1 << XER_OV));

    }

    tcg_gen_br(l2);

    gen_set_label(l1);

    tcg_gen_mov_tl(ret, arg1);

    if (ov_check) {

        tcg_gen_ori_tl(cpu_xer, cpu_xer, (1 << XER_OV) | (1 << XER_SO));

    }

    gen_set_label(l2);

    if (unlikely(Rc(ctx->opcode) != 0))

        gen_set_Rc0(ctx, ret);

}

```

## H2R-062

### Query

```c

static AVInputFormat *probe_input_format(AVProbeData *pd, int is_opened)

{

    AVInputFormat *fmt1, *fmt;

    int score, score_max;



    fmt = NULL;

    score_max = 0;

    for(fmt1 = first_iformat; fmt1 != NULL; fmt1 = fmt1->next) {

        if (!is_opened && !(fmt1->flags & AVFMT_NOFILE))

            continue;

        score = 0;

        if (fmt1->extensions) {

            if (match_ext(pd->filename, fmt1->extensions)) {

                score = 50;

            }

        } else if (fmt1->read_probe) {

            score = fmt1->read_probe(pd);

        }

        if (score > score_max) {

            score_max = score;

            fmt = fmt1;

        }

    }

    return fmt;

}

```

### Demonstration

```c

int qdev_prop_check_globals(void)

{

    GlobalProperty *prop;

    int ret = 0;



    QTAILQ_FOREACH(prop, &global_props, next) {

        ObjectClass *oc;

        DeviceClass *dc;

        if (prop->used) {

            continue;

        }

        if (!prop->user_provided) {

            continue;

        }

        oc = object_class_by_name(prop->driver);

        oc = object_class_dynamic_cast(oc, TYPE_DEVICE);

        if (!oc) {

            error_report("Warning: global %s.%s has invalid class name",

                       prop->driver, prop->property);

            ret = 1;

            continue;

        }

        dc = DEVICE_CLASS(oc);

        if (!dc->hotpluggable && !prop->used) {

            error_report("Warning: global %s.%s=%s not used",

                       prop->driver, prop->property, prop->value);

            ret = 1;

            continue;

        }

    }

    return ret;

}

```

## H2R-063

### Query

```c

static void do_busid_cmd(ESPState *s, uint8_t *buf, uint8_t busid)

{

    int32_t datalen;

    int lun;



    DPRINTF("do_busid_cmd: busid 0x%x\n", busid);

    lun = busid & 7;

    s->current_req = scsi_req_new(s->current_dev, 0, lun, NULL);

    datalen = scsi_req_enqueue(s->current_req, buf);

    s->ti_size = datalen;

    if (datalen != 0) {

        s->rregs[ESP_RSTAT] = STAT_TC;

        s->dma_left = 0;

        s->dma_counter = 0;

        if (datalen > 0) {

            s->rregs[ESP_RSTAT] |= STAT_DI;

        } else {

            s->rregs[ESP_RSTAT] |= STAT_DO;

        }

        scsi_req_continue(s->current_req);

    }

    s->rregs[ESP_RINTR] = INTR_BS | INTR_FC;

    s->rregs[ESP_RSEQ] = SEQ_CD;

    esp_raise_irq(s);

}

```

### Demonstration

```c

static void shpc_interrupt_update(PCIDevice *d)

{

    SHPCDevice *shpc = d->shpc;

    int slot;

    int level = 0;

    uint32_t serr_int;

    uint32_t int_locator = 0;



    /* Update interrupt locator register */

    for (slot = 0; slot < shpc->nslots; ++slot) {

        uint8_t event = shpc->config[SHPC_SLOT_EVENT_LATCH(slot)];

        uint8_t disable = shpc->config[SHPC_SLOT_EVENT_SERR_INT_DIS(d, slot)];

        uint32_t mask = 1 << SHPC_IDX_TO_LOGICAL(slot);

        if (event & ~disable) {

            int_locator |= mask;

        }

    }

    serr_int = pci_get_long(shpc->config + SHPC_SERR_INT);

    if ((serr_int & SHPC_CMD_DETECTED) && !(serr_int & SHPC_CMD_INT_DIS)) {

        int_locator |= SHPC_INT_COMMAND;

    }

    pci_set_long(shpc->config + SHPC_INT_LOCATOR, int_locator);

    level = (!(serr_int & SHPC_INT_DIS) && int_locator) ? 1 : 0;

    if (msi_enabled(d) && shpc->msi_requested != level)

        msi_notify(d, 0);

    else

        pci_set_irq(d, level);

    shpc->msi_requested = level;

}

```

## H2R-064

### Query

```c

static int mp3lame_encode_frame(AVCodecContext *avctx, AVPacket *avpkt,

                                const AVFrame *frame, int *got_packet_ptr)

{

    LAMEContext *s = avctx->priv_data;

    MPADecodeHeader hdr;

    int len, ret, ch;

    int lame_result;

    uint32_t h;



    if (frame) {

        switch (avctx->sample_fmt) {

        case AV_SAMPLE_FMT_S16P:

            ENCODE_BUFFER(lame_encode_buffer, int16_t, frame->data);

            break;

        case AV_SAMPLE_FMT_S32P:

            ENCODE_BUFFER(lame_encode_buffer_int, int32_t, frame->data);

            break;

        case AV_SAMPLE_FMT_FLTP:

            if (frame->linesize[0] < 4 * FFALIGN(frame->nb_samples, 8)) {

                av_log(avctx, AV_LOG_ERROR, "inadequate AVFrame plane padding\n");

                return AVERROR(EINVAL);

            }

            for (ch = 0; ch < avctx->channels; ch++) {

                s->fdsp.vector_fmul_scalar(s->samples_flt[ch],

                                           (const float *)frame->data[ch],

                                           32768.0f,

                                           FFALIGN(frame->nb_samples, 8));

            }

            ENCODE_BUFFER(lame_encode_buffer_float, float, s->samples_flt);

            break;

        default:

            return AVERROR_BUG;

        }

    } else {

        lame_result = lame_encode_flush(s->gfp, s->buffer + s->buffer_index,

                                        s->buffer_size - s->buffer_index);

    }

    if (lame_result < 0) {

        if (lame_result == -1) {

            av_log(avctx, AV_LOG_ERROR,

                   "lame: output buffer too small (buffer index: %d, free bytes: %d)\n",

                   s->buffer_index, s->buffer_size - s->buffer_index);

        }

        return -1;

    }

    s->buffer_index += lame_result;

    ret = realloc_buffer(s);

    if (ret < 0) {

        av_log(avctx, AV_LOG_ERROR, "error reallocating output buffer\n");

        return ret;

    }



    /* add current frame to the queue */

    if (frame) {

        if ((ret = ff_af_queue_add(&s->afq, frame)) < 0)

            return ret;

    }



    /* Move 1 frame from the LAME buffer to the output packet, if available.

       We have to parse the first frame header in the output buffer to

       determine the frame size. */

    if (s->buffer_index < 4)

        return 0;

    h = AV_RB32(s->buffer);

    if (ff_mpa_check_header(h) < 0) {

        av_log(avctx, AV_LOG_ERROR, "Invalid mp3 header at start of buffer\n");

        return AVERROR_BUG;

    }

    if (avpriv_mpegaudio_decode_header(&hdr, h)) {

        av_log(avctx, AV_LOG_ERROR, "free format output not supported\n");

        return -1;

    }

    len = hdr.frame_size;

    ff_dlog(avctx, "in:%d packet-len:%d index:%d\n", avctx->frame_size, len,

            s->buffer_index);

    if (len <= s->buffer_index) {

        if ((ret = ff_alloc_packet(avpkt, len))) {

            av_log(avctx, AV_LOG_ERROR, "Error getting output packet\n");

            return ret;

        }

        memcpy(avpkt->data, s->buffer, len);

        s->buffer_index -= len;

        memmove(s->buffer, s->buffer + len, s->buffer_index);



        /* Get the next frame pts/duration */

        ff_af_queue_remove(&s->afq, avctx->frame_size, &avpkt->pts,

                           &avpkt->duration);



        avpkt->size = len;

        *got_packet_ptr = 1;

    }

    return 0;

}

```

### Demonstration

```c

static int libshine_encode_frame(AVCodecContext *avctx, AVPacket *avpkt,

                                 const AVFrame *frame, int *got_packet_ptr)

{

    SHINEContext *s = avctx->priv_data;

    MPADecodeHeader hdr;

    unsigned char *data;

    long written;

    int ret, len;



    if (frame)

        data = shine_encode_buffer(s->shine, (int16_t **)frame->data, &written);

    else

        data = shine_flush(s->shine, &written);

    if (written < 0)

        return -1;

    if (written > 0) {

        if (s->buffer_index + written > BUFFER_SIZE) {

            av_log(avctx, AV_LOG_ERROR, "internal buffer too small\n");

            return AVERROR_BUG;

        }

        memcpy(s->buffer + s->buffer_index, data, written);

        s->buffer_index += written;

    }

    if (frame) {

        if ((ret = ff_af_queue_add(&s->afq, frame)) < 0)

            return ret;

    }



    if (s->buffer_index < 4 || !s->afq.frame_count)

        return 0;

    if (avpriv_mpegaudio_decode_header(&hdr, AV_RB32(s->buffer))) {

        av_log(avctx, AV_LOG_ERROR, "free format output not supported\n");

        return -1;

    }



    len = hdr.frame_size;

    if (len <= s->buffer_index) {

        if ((ret = ff_alloc_packet2(avctx, avpkt, len)))

            return ret;

        memcpy(avpkt->data, s->buffer, len);

        s->buffer_index -= len;

        memmove(s->buffer, s->buffer + len, s->buffer_index);



        ff_af_queue_remove(&s->afq, avctx->frame_size, &avpkt->pts,

                           &avpkt->duration);



        avpkt->size = len;

        *got_packet_ptr = 1;

    }

    return 0;

}

```

## H2R-065

### Query

```c

static void vvfat_close(BlockDriverState *bs)

{

    BDRVVVFATState *s = bs->opaque;



    vvfat_close_current_file(s);

    array_free(&(s->fat));

    array_free(&(s->directory));

    array_free(&(s->mapping));

    if(s->cluster_buffer)

        free(s->cluster_buffer);

}

```

### Demonstration

```c

static void phys_sections_free(PhysPageMap *map)

{

    while (map->sections_nb > 0) {

        MemoryRegionSection *section = &map->sections[--map->sections_nb];

        phys_section_destroy(section->mr);

    }

    g_free(map->sections);

    g_free(map->nodes);

    g_free(map);

}

```

## H2R-066

### Query

```c

static int opt_new_stream(const char *opt, const char *arg)

{

    AVFormatContext *oc;

    if (nb_output_files <= 0) {

        fprintf(stderr, "At least one output file must be specified\n");

        ffmpeg_exit(1);

    }

    oc = output_files[nb_output_files - 1];



    if      (!strcmp(opt, "newvideo"   )) new_video_stream   (oc);

    else if (!strcmp(opt, "newaudio"   )) new_audio_stream   (oc);

    else if (!strcmp(opt, "newsubtitle")) new_subtitle_stream(oc);

    else av_assert0(0);

    return 0;

}

```

### Demonstration

```c

static int mon_init_func(void *opaque, QemuOpts *opts, Error **errp)

{

    CharDriverState *chr;

    const char *chardev;

    const char *mode;

    int flags;



    mode = qemu_opt_get(opts, "mode");

    if (mode == NULL) {

        mode = "readline";

    }

    if (strcmp(mode, "readline") == 0) {

        flags = MONITOR_USE_READLINE;

    } else if (strcmp(mode, "control") == 0) {

        flags = MONITOR_USE_CONTROL;

    } else {

        fprintf(stderr, "unknown monitor mode \"%s\"\n", mode);

        exit(1);

    }



    if (qemu_opt_get_bool(opts, "pretty", 0))

        flags |= MONITOR_USE_PRETTY;



    if (qemu_opt_get_bool(opts, "default", 0))

        flags |= MONITOR_IS_DEFAULT;



    chardev = qemu_opt_get(opts, "chardev");

    chr = qemu_chr_find(chardev);

    if (chr == NULL) {

        fprintf(stderr, "chardev \"%s\" not found\n", chardev);

        exit(1);

    }



    qemu_chr_fe_claim_no_fail(chr);

    monitor_init(chr, flags);

    return 0;

}

```

## H2R-067

### Query

```c

static void virtio_scsi_complete_req(VirtIOSCSIReq *req)

{

    VirtIOSCSI *s = req->dev;

    VirtQueue *vq = req->vq;

    VirtIODevice *vdev = VIRTIO_DEVICE(s);



    qemu_iovec_from_buf(&req->resp_iov, 0, &req->resp, req->resp_size);

    virtqueue_push(vq, &req->elem, req->qsgl.size + req->resp_iov.size);

    if (s->dataplane_started && !s->dataplane_fenced) {

        virtio_scsi_dataplane_notify(vdev, req);

    } else {

        virtio_notify(vdev, vq);

    }



    if (req->sreq) {

        req->sreq->hba_private = NULL;

        scsi_req_unref(req->sreq);

    }

    virtio_scsi_free_req(req);

}

```

### Demonstration

```c

bool virtio_scsi_handle_cmd_vq(VirtIOSCSI *s, VirtQueue *vq)

{

    VirtIOSCSIReq *req, *next;

    int ret = 0;

    bool progress = false;



    QTAILQ_HEAD(, VirtIOSCSIReq) reqs = QTAILQ_HEAD_INITIALIZER(reqs);



    virtio_scsi_acquire(s);

    do {

        virtio_queue_set_notification(vq, 0);



        while ((req = virtio_scsi_pop_req(s, vq))) {

            progress = true;

            ret = virtio_scsi_handle_cmd_req_prepare(s, req);

            if (!ret) {

                QTAILQ_INSERT_TAIL(&reqs, req, next);

            } else if (ret == -EINVAL) {

                /* The device is broken and shouldn't process any request */

                while (!QTAILQ_EMPTY(&reqs)) {

                    req = QTAILQ_FIRST(&reqs);

                    QTAILQ_REMOVE(&reqs, req, next);

                    blk_io_unplug(req->sreq->dev->conf.blk);

                    scsi_req_unref(req->sreq);

                    virtqueue_detach_element(req->vq, &req->elem, 0);

                    virtio_scsi_free_req(req);

                }

            }

        }



        virtio_queue_set_notification(vq, 1);

    } while (ret != -EINVAL && !virtio_queue_empty(vq));



    QTAILQ_FOREACH_SAFE(req, &reqs, next, next) {

        virtio_scsi_handle_cmd_req_submit(s, req);

    }

    virtio_scsi_release(s);

    return progress;

}

```

## H2R-068

### Query

```c

static int encode_frame(AVCodecContext * avctx, AVPacket *pkt,

                        const AVFrame *pict, int *got_packet)

{

    TiffEncoderContext *s = avctx->priv_data;

    AVFrame *const p = &s->picture;

    int i;

    uint8_t *ptr;

    uint8_t *offset;

    uint32_t strips;

    uint32_t *strip_sizes = NULL;

    uint32_t *strip_offsets = NULL;

    int bytes_per_row;

    uint32_t res[2] = { 72, 1 };        // image resolution (72/1)

    uint16_t bpp_tab[] = { 8, 8, 8, 8 };

    int ret;

    int is_yuv = 0;

    uint8_t *yuv_line = NULL;

    int shift_h, shift_v;

    const AVPixFmtDescriptor* pfd;



    s->avctx = avctx;



    *p = *pict;

    p->pict_type = AV_PICTURE_TYPE_I;

    p->key_frame = 1;

    avctx->coded_frame= &s->picture;



    s->width = avctx->width;

    s->height = avctx->height;

    s->subsampling[0] = 1;

    s->subsampling[1] = 1;



    switch (avctx->pix_fmt) {

    case PIX_FMT_RGB48LE:

    case PIX_FMT_GRAY16LE:

    case PIX_FMT_RGB24:

    case PIX_FMT_GRAY8:

    case PIX_FMT_PAL8:

        pfd = &av_pix_fmt_descriptors[avctx->pix_fmt];

        s->bpp = av_get_bits_per_pixel(pfd);

        if (pfd->flags & PIX_FMT_PAL) {

            s->photometric_interpretation = 3;

        } else if (pfd->flags & PIX_FMT_RGB) {

            s->photometric_interpretation = 2;

        } else {

            s->photometric_interpretation = 1;

        }

        s->bpp_tab_size = pfd->nb_components;

        for (i = 0; i < s->bpp_tab_size; i++) {

            bpp_tab[i] = s->bpp / s->bpp_tab_size;

        }

        break;

    case PIX_FMT_MONOBLACK:

        s->bpp = 1;

        s->photometric_interpretation = 1;

        s->bpp_tab_size = 0;

        break;

    case PIX_FMT_MONOWHITE:

        s->bpp = 1;

        s->photometric_interpretation = 0;

        s->bpp_tab_size = 0;

        break;

    case PIX_FMT_YUV420P:

    case PIX_FMT_YUV422P:

    case PIX_FMT_YUV444P:

    case PIX_FMT_YUV410P:

    case PIX_FMT_YUV411P:

        s->photometric_interpretation = 6;

        avcodec_get_chroma_sub_sample(avctx->pix_fmt,

                &shift_h, &shift_v);

        s->bpp = 8 + (16 >> (shift_h + shift_v));

        s->subsampling[0] = 1 << shift_h;

        s->subsampling[1] = 1 << shift_v;

        s->bpp_tab_size = 3;

        is_yuv = 1;

        break;

    default:

        av_log(s->avctx, AV_LOG_ERROR,

               "This colors format is not supported\n");

        return -1;

    }



    if (s->compr == TIFF_DEFLATE || s->compr == TIFF_ADOBE_DEFLATE || s->compr == TIFF_LZW)

        //best choose for DEFLATE

        s->rps = s->height;

    else

        s->rps = FFMAX(8192 / (((s->width * s->bpp) >> 3) + 1), 1);     // suggest size of strip

    s->rps = ((s->rps - 1) / s->subsampling[1] + 1) * s->subsampling[1]; // round rps up



    strips = (s->height - 1) / s->rps + 1;



    if (!pkt->data &&

        (ret = av_new_packet(pkt, avctx->width * avctx->height * s->bpp * 2 +

                                  avctx->height * 4 + FF_MIN_BUFFER_SIZE)) < 0) {

        av_log(avctx, AV_LOG_ERROR, "Error getting output packet.\n");

        return ret;

    }

    ptr          = pkt->data;

    s->buf_start = pkt->data;

    s->buf       = &ptr;

    s->buf_size  = pkt->size;



    if (check_size(s, 8))

        goto fail;



    // write header

    bytestream_put_le16(&ptr, 0x4949);

    bytestream_put_le16(&ptr, 42);



    offset = ptr;

    bytestream_put_le32(&ptr, 0);



    strip_sizes = av_mallocz(sizeof(*strip_sizes) * strips);

    strip_offsets = av_mallocz(sizeof(*strip_offsets) * strips);



    bytes_per_row = (((s->width - 1)/s->subsampling[0] + 1) * s->bpp

                    * s->subsampling[0] * s->subsampling[1] + 7) >> 3;

    if (is_yuv){

        yuv_line = av_malloc(bytes_per_row);

        if (yuv_line == NULL){

            av_log(s->avctx, AV_LOG_ERROR, "Not enough memory\n");

            goto fail;

        }

    }



#if CONFIG_ZLIB

    if (s->compr == TIFF_DEFLATE || s->compr == TIFF_ADOBE_DEFLATE) {

        uint8_t *zbuf;

        int zlen, zn;

        int j;



        zlen = bytes_per_row * s->rps;

        zbuf = av_malloc(zlen);

        strip_offsets[0] = ptr - pkt->data;

        zn = 0;

        for (j = 0; j < s->rps; j++) {

            if (is_yuv){

                pack_yuv(s, yuv_line, j);

                memcpy(zbuf + zn, yuv_line, bytes_per_row);

                j += s->subsampling[1] - 1;

            }

            else

                memcpy(zbuf + j * bytes_per_row,

                       p->data[0] + j * p->linesize[0], bytes_per_row);

            zn += bytes_per_row;

        }

        ret = encode_strip(s, zbuf, ptr, zn, s->compr);

        av_free(zbuf);

        if (ret < 0) {

            av_log(s->avctx, AV_LOG_ERROR, "Encode strip failed\n");

            goto fail;

        }

        ptr += ret;

        strip_sizes[0] = ptr - pkt->data - strip_offsets[0];

    } else

#endif

    {

        if(s->compr == TIFF_LZW)

            s->lzws = av_malloc(ff_lzw_encode_state_size);

        for (i = 0; i < s->height; i++) {

            if (strip_sizes[i / s->rps] == 0) {

                if(s->compr == TIFF_LZW){

                    ff_lzw_encode_init(s->lzws, ptr, s->buf_size - (*s->buf - s->buf_start),

                                       12, FF_LZW_TIFF, put_bits);

                }

                strip_offsets[i / s->rps] = ptr - pkt->data;

            }

            if (is_yuv){

                 pack_yuv(s, yuv_line, i);

                 ret = encode_strip(s, yuv_line, ptr, bytes_per_row, s->compr);

                 i += s->subsampling[1] - 1;

            }

            else

                ret = encode_strip(s, p->data[0] + i * p->linesize[0],

                        ptr, bytes_per_row, s->compr);

            if (ret < 0) {

                av_log(s->avctx, AV_LOG_ERROR, "Encode strip failed\n");

                goto fail;

            }

            strip_sizes[i / s->rps] += ret;

            ptr += ret;

            if(s->compr == TIFF_LZW && (i==s->height-1 || i%s->rps == s->rps-1)){

                ret = ff_lzw_encode_flush(s->lzws, flush_put_bits);

                strip_sizes[(i / s->rps )] += ret ;

                ptr += ret;

            }

        }

        if(s->compr == TIFF_LZW)

            av_free(s->lzws);

    }



    s->num_entries = 0;



    add_entry1(s,TIFF_SUBFILE,           TIFF_LONG,             0);

    add_entry1(s,TIFF_WIDTH,             TIFF_LONG,             s->width);

    add_entry1(s,TIFF_HEIGHT,            TIFF_LONG,             s->height);



    if (s->bpp_tab_size)

    add_entry(s, TIFF_BPP,               TIFF_SHORT,    s->bpp_tab_size, bpp_tab);



    add_entry1(s,TIFF_COMPR,             TIFF_SHORT,            s->compr);

    add_entry1(s,TIFF_INVERT,            TIFF_SHORT,            s->photometric_interpretation);

    add_entry(s, TIFF_STRIP_OFFS,        TIFF_LONG,     strips, strip_offsets);



    if (s->bpp_tab_size)

    add_entry1(s,TIFF_SAMPLES_PER_PIXEL, TIFF_SHORT,            s->bpp_tab_size);



    add_entry1(s,TIFF_ROWSPERSTRIP,      TIFF_LONG,             s->rps);

    add_entry(s, TIFF_STRIP_SIZE,        TIFF_LONG,     strips, strip_sizes);

    add_entry(s, TIFF_XRES,              TIFF_RATIONAL, 1,      res);

    add_entry(s, TIFF_YRES,              TIFF_RATIONAL, 1,      res);

    add_entry1(s,TIFF_RES_UNIT,          TIFF_SHORT,            2);



    if(!(avctx->flags & CODEC_FLAG_BITEXACT))

    add_entry(s, TIFF_SOFTWARE_NAME,     TIFF_STRING,

              strlen(LIBAVCODEC_IDENT) + 1, LIBAVCODEC_IDENT);



    if (avctx->pix_fmt == PIX_FMT_PAL8) {

        uint16_t pal[256 * 3];

        for (i = 0; i < 256; i++) {

            uint32_t rgb = *(uint32_t *) (p->data[1] + i * 4);

            pal[i]       = ((rgb >> 16) & 0xff) * 257;

            pal[i + 256] = ((rgb >> 8 ) & 0xff) * 257;

            pal[i + 512] = ( rgb        & 0xff) * 257;

        }

        add_entry(s, TIFF_PAL, TIFF_SHORT, 256 * 3, pal);

    }

    if (is_yuv){

        /** according to CCIR Recommendation 601.1 */

        uint32_t refbw[12] = {15, 1, 235, 1, 128, 1, 240, 1, 128, 1, 240, 1};

        add_entry(s, TIFF_YCBCR_SUBSAMPLING, TIFF_SHORT,    2, s->subsampling);

        add_entry(s, TIFF_REFERENCE_BW,      TIFF_RATIONAL, 6, refbw);

    }

    bytestream_put_le32(&offset, ptr - pkt->data);    // write offset to dir



    if (check_size(s, 6 + s->num_entries * 12)) {

        ret = AVERROR(EINVAL);

        goto fail;

    }

    bytestream_put_le16(&ptr, s->num_entries);  // write tag count

    bytestream_put_buffer(&ptr, s->entries, s->num_entries * 12);

    bytestream_put_le32(&ptr, 0);



    pkt->size   = ptr - pkt->data;

    pkt->flags |= AV_PKT_FLAG_KEY;

    *got_packet = 1;



fail:

    av_free(strip_sizes);

    av_free(strip_offsets);

    av_free(yuv_line);

    return ret;

}

```

### Demonstration

```c

static int encode_frame(AVCodecContext *avctx, AVPacket *pkt,

                        const AVFrame *pict, int *got_packet)

{

    TiffEncoderContext *s = avctx->priv_data;

    const AVFrame *const p = pict;

    int i;

    uint8_t *ptr;

    uint8_t *offset;

    uint32_t strips;

    uint32_t *strip_sizes   = NULL;

    uint32_t *strip_offsets = NULL;

    int bytes_per_row;

    uint32_t res[2]    = { 72, 1 };     // image resolution (72/1)

    uint16_t bpp_tab[] = { 8, 8, 8, 8 };

    int ret;

    int is_yuv = 0;

    uint8_t *yuv_line = NULL;

    int shift_h, shift_v;

    int packet_size;

    const AVPixFmtDescriptor *pfd;



    s->avctx = avctx;



    s->width          = avctx->width;

    s->height         = avctx->height;

    s->subsampling[0] = 1;

    s->subsampling[1] = 1;



    switch (avctx->pix_fmt) {

    case AV_PIX_FMT_RGB48LE:

    case AV_PIX_FMT_GRAY16LE:

    case AV_PIX_FMT_RGBA:

    case AV_PIX_FMT_RGB24:

    case AV_PIX_FMT_GRAY8:

    case AV_PIX_FMT_PAL8:

        pfd    = av_pix_fmt_desc_get(avctx->pix_fmt);

        s->bpp = av_get_bits_per_pixel(pfd);

        if (pfd->flags & AV_PIX_FMT_FLAG_PAL)

            s->photometric_interpretation = TIFF_PHOTOMETRIC_PALETTE;

        else if (pfd->flags & AV_PIX_FMT_FLAG_RGB)

            s->photometric_interpretation = TIFF_PHOTOMETRIC_RGB;

        else

            s->photometric_interpretation = TIFF_PHOTOMETRIC_BLACK_IS_ZERO;

        s->bpp_tab_size = pfd->nb_components;

        for (i = 0; i < s->bpp_tab_size; i++)

            bpp_tab[i] = s->bpp / s->bpp_tab_size;

        break;

    case AV_PIX_FMT_MONOBLACK:

        s->bpp                        = 1;

        s->photometric_interpretation = TIFF_PHOTOMETRIC_BLACK_IS_ZERO;

        s->bpp_tab_size               = 0;

        break;

    case AV_PIX_FMT_MONOWHITE:

        s->bpp                        = 1;

        s->photometric_interpretation = TIFF_PHOTOMETRIC_WHITE_IS_ZERO;

        s->bpp_tab_size               = 0;

        break;

    case AV_PIX_FMT_YUV420P:

    case AV_PIX_FMT_YUV422P:

    case AV_PIX_FMT_YUV444P:

    case AV_PIX_FMT_YUV410P:

    case AV_PIX_FMT_YUV411P:

        av_pix_fmt_get_chroma_sub_sample(avctx->pix_fmt, &shift_h, &shift_v);

        s->photometric_interpretation = TIFF_PHOTOMETRIC_YCBCR;

        s->bpp                        = 8 + (16 >> (shift_h + shift_v));

        s->subsampling[0]             = 1 << shift_h;

        s->subsampling[1]             = 1 << shift_v;

        s->bpp_tab_size               = 3;

        is_yuv                        = 1;

        break;

    default:

        av_log(s->avctx, AV_LOG_ERROR,

               "This colors format is not supported\n");

        return -1;

    }



    if (s->compr == TIFF_DEFLATE       ||

        s->compr == TIFF_ADOBE_DEFLATE ||

        s->compr == TIFF_LZW)

        // best choice for DEFLATE

        s->rps = s->height;

    else

        // suggest size of strip

        s->rps = FFMAX(8192 / (((s->width * s->bpp) >> 3) + 1), 1);

    // round rps up

    s->rps = ((s->rps - 1) / s->subsampling[1] + 1) * s->subsampling[1];



    strips = (s->height - 1) / s->rps + 1;



    packet_size = avctx->height * ((avctx->width * s->bpp + 7) >> 3) * 2 +

                  avctx->height * 4 + FF_MIN_BUFFER_SIZE;



    if (!pkt->data &&

        (ret = av_new_packet(pkt, packet_size)) < 0) {

        av_log(avctx, AV_LOG_ERROR, "Error getting output packet.\n");

        return ret;

    }

    ptr          = pkt->data;

    s->buf_start = pkt->data;

    s->buf       = &ptr;

    s->buf_size  = pkt->size;



    if (check_size(s, 8))

        goto fail;



    // write header

    bytestream_put_le16(&ptr, 0x4949);

    bytestream_put_le16(&ptr, 42);



    offset = ptr;

    bytestream_put_le32(&ptr, 0);



    strip_sizes   = av_mallocz_array(strips, sizeof(*strip_sizes));

    strip_offsets = av_mallocz_array(strips, sizeof(*strip_offsets));

    if (!strip_sizes || !strip_offsets) {

        ret = AVERROR(ENOMEM);

        goto fail;

    }



    bytes_per_row = (((s->width - 1) / s->subsampling[0] + 1) * s->bpp *

                     s->subsampling[0] * s->subsampling[1] + 7) >> 3;

    if (is_yuv) {

        yuv_line = av_malloc(bytes_per_row);

        if (!yuv_line) {

            av_log(s->avctx, AV_LOG_ERROR, "Not enough memory\n");

            ret = AVERROR(ENOMEM);

            goto fail;

        }

    }



#if CONFIG_ZLIB

    if (s->compr == TIFF_DEFLATE || s->compr == TIFF_ADOBE_DEFLATE) {

        uint8_t *zbuf;

        int zlen, zn;

        int j;



        zlen = bytes_per_row * s->rps;

        zbuf = av_malloc(zlen);

        if (!zbuf) {

            ret = AVERROR(ENOMEM);

            goto fail;

        }

        strip_offsets[0] = ptr - pkt->data;

        zn               = 0;

        for (j = 0; j < s->rps; j++) {

            if (is_yuv) {

                pack_yuv(s, p, yuv_line, j);

                memcpy(zbuf + zn, yuv_line, bytes_per_row);

                j += s->subsampling[1] - 1;

            } else

                memcpy(zbuf + j * bytes_per_row,

                       p->data[0] + j * p->linesize[0], bytes_per_row);

            zn += bytes_per_row;

        }

        ret = encode_strip(s, zbuf, ptr, zn, s->compr);

        av_free(zbuf);

        if (ret < 0) {

            av_log(s->avctx, AV_LOG_ERROR, "Encode strip failed\n");

            goto fail;

        }

        ptr           += ret;

        strip_sizes[0] = ptr - pkt->data - strip_offsets[0];

    } else

#endif

    if (s->compr == TIFF_LZW) {

        s->lzws = av_malloc(ff_lzw_encode_state_size);

        if (!s->lzws) {

            ret = AVERROR(ENOMEM);

            goto fail;

        }

    }

    for (i = 0; i < s->height; i++) {

        if (strip_sizes[i / s->rps] == 0) {

            if (s->compr == TIFF_LZW) {

                ff_lzw_encode_init(s->lzws, ptr,

                                   s->buf_size - (*s->buf - s->buf_start),

                                   12, FF_LZW_TIFF, put_bits);

            }

            strip_offsets[i / s->rps] = ptr - pkt->data;

        }

        if (is_yuv) {

            pack_yuv(s, p, yuv_line, i);

            ret = encode_strip(s, yuv_line, ptr, bytes_per_row, s->compr);

            i  += s->subsampling[1] - 1;

        } else

            ret = encode_strip(s, p->data[0] + i * p->linesize[0],

                               ptr, bytes_per_row, s->compr);

        if (ret < 0) {

            av_log(s->avctx, AV_LOG_ERROR, "Encode strip failed\n");

            goto fail;

        }

        strip_sizes[i / s->rps] += ret;

        ptr                     += ret;

        if (s->compr == TIFF_LZW &&

            (i == s->height - 1 || i % s->rps == s->rps - 1)) {

            ret = ff_lzw_encode_flush(s->lzws, flush_put_bits);

            strip_sizes[(i / s->rps)] += ret;

            ptr                       += ret;

        }

    }

    if (s->compr == TIFF_LZW)

        av_free(s->lzws);



    s->num_entries = 0;



    add_entry1(s, TIFF_SUBFILE, TIFF_LONG, 0);

    add_entry1(s, TIFF_WIDTH,   TIFF_LONG, s->width);

    add_entry1(s, TIFF_HEIGHT,  TIFF_LONG, s->height);



    if (s->bpp_tab_size)

        add_entry(s, TIFF_BPP, TIFF_SHORT, s->bpp_tab_size, bpp_tab);



    add_entry1(s, TIFF_COMPR,       TIFF_SHORT, s->compr);

    add_entry1(s, TIFF_PHOTOMETRIC, TIFF_SHORT, s->photometric_interpretation);

    add_entry(s,  TIFF_STRIP_OFFS,  TIFF_LONG,  strips, strip_offsets);



    if (s->bpp_tab_size)

        add_entry1(s, TIFF_SAMPLES_PER_PIXEL, TIFF_SHORT, s->bpp_tab_size);



    add_entry1(s, TIFF_ROWSPERSTRIP, TIFF_LONG,     s->rps);

    add_entry(s,  TIFF_STRIP_SIZE,   TIFF_LONG,     strips, strip_sizes);

    add_entry(s,  TIFF_XRES,         TIFF_RATIONAL, 1,      res);

    add_entry(s,  TIFF_YRES,         TIFF_RATIONAL, 1,      res);

    add_entry1(s, TIFF_RES_UNIT,     TIFF_SHORT,    2);



    if (!(avctx->flags & CODEC_FLAG_BITEXACT))

        add_entry(s, TIFF_SOFTWARE_NAME, TIFF_STRING,

                  strlen(LIBAVCODEC_IDENT) + 1, LIBAVCODEC_IDENT);



    if (avctx->pix_fmt == AV_PIX_FMT_PAL8) {

        uint16_t pal[256 * 3];

        for (i = 0; i < 256; i++) {

            uint32_t rgb = *(uint32_t *) (p->data[1] + i * 4);

            pal[i]       = ((rgb >> 16) & 0xff) * 257;

            pal[i + 256] = ((rgb >>  8) & 0xff) * 257;

            pal[i + 512] =  (rgb        & 0xff) * 257;

        }

        add_entry(s, TIFF_PAL, TIFF_SHORT, 256 * 3, pal);

    }

    if (is_yuv) {

        /** according to CCIR Recommendation 601.1 */

        uint32_t refbw[12] = { 15, 1, 235, 1, 128, 1, 240, 1, 128, 1, 240, 1 };

        add_entry(s, TIFF_YCBCR_SUBSAMPLING, TIFF_SHORT,    2, s->subsampling);

        add_entry(s, TIFF_REFERENCE_BW,      TIFF_RATIONAL, 6, refbw);

    }

    // write offset to dir

    bytestream_put_le32(&offset, ptr - pkt->data);



    if (check_size(s, 6 + s->num_entries * 12)) {

        ret = AVERROR(EINVAL);

        goto fail;

    }

    bytestream_put_le16(&ptr, s->num_entries);  // write tag count

    bytestream_put_buffer(&ptr, s->entries, s->num_entries * 12);

    bytestream_put_le32(&ptr, 0);



    pkt->size   = ptr - pkt->data;

    pkt->flags |= AV_PKT_FLAG_KEY;

    *got_packet = 1;



fail:

    av_free(strip_sizes);

    av_free(strip_offsets);

    av_free(yuv_line);

    return ret;

}

```

## H2R-069

### Query

```c

yuv2rgba64_2_c_template(SwsContext *c, const int32_t *buf[2],

                       const int32_t *ubuf[2], const int32_t *vbuf[2],

                       const int32_t *abuf[2], uint16_t *dest, int dstW,

                       int yalpha, int uvalpha, int y,

                       enum AVPixelFormat target, int hasAlpha, int eightbytes)

{

    const int32_t *buf0  = buf[0],  *buf1  = buf[1],

                  *ubuf0 = ubuf[0], *ubuf1 = ubuf[1],

                  *vbuf0 = vbuf[0], *vbuf1 = vbuf[1],

                  *abuf0 = hasAlpha ? abuf[0] : NULL,

                  *abuf1 = hasAlpha ? abuf[1] : NULL;

    int  yalpha1 = 4096 - yalpha;

    int uvalpha1 = 4096 - uvalpha;

    int i;

    int A1 = 0xffff<<14, A2 = 0xffff<<14;



    for (i = 0; i < ((dstW + 1) >> 1); i++) {

        int Y1 = (buf0[i * 2]     * yalpha1  + buf1[i * 2]     * yalpha) >> 14;

        int Y2 = (buf0[i * 2 + 1] * yalpha1  + buf1[i * 2 + 1] * yalpha) >> 14;

        int U  = (ubuf0[i]        * uvalpha1 + ubuf1[i]        * uvalpha + (-128 << 23)) >> 14;

        int V  = (vbuf0[i]        * uvalpha1 + vbuf1[i]        * uvalpha + (-128 << 23)) >> 14;

        int R, G, B;



        Y1 -= c->yuv2rgb_y_offset;

        Y2 -= c->yuv2rgb_y_offset;

        Y1 *= c->yuv2rgb_y_coeff;

        Y2 *= c->yuv2rgb_y_coeff;

        Y1 += 1 << 13;

        Y2 += 1 << 13;



        R = V * c->yuv2rgb_v2r_coeff;

        G = V * c->yuv2rgb_v2g_coeff + U * c->yuv2rgb_u2g_coeff;

        B =                            U * c->yuv2rgb_u2b_coeff;



        if (hasAlpha) {

            A1 = (abuf0[i * 2    ] * yalpha1 + abuf1[i * 2    ] * yalpha) >> 1;

            A2 = (abuf0[i * 2 + 1] * yalpha1 + abuf1[i * 2 + 1] * yalpha) >> 1;



            A1 += 1 << 13;

            A2 += 1 << 13;

        }



        output_pixel(&dest[0], av_clip_uintp2(R_B + Y1, 30) >> 14);

        output_pixel(&dest[1], av_clip_uintp2(  G + Y1, 30) >> 14);

        output_pixel(&dest[2], av_clip_uintp2(B_R + Y1, 30) >> 14);

        if (eightbytes) {

            output_pixel(&dest[3], av_clip_uintp2(A1      , 30) >> 14);

            output_pixel(&dest[4], av_clip_uintp2(R_B + Y2, 30) >> 14);

            output_pixel(&dest[5], av_clip_uintp2(  G + Y2, 30) >> 14);

            output_pixel(&dest[6], av_clip_uintp2(B_R + Y2, 30) >> 14);

            output_pixel(&dest[7], av_clip_uintp2(A2      , 30) >> 14);

            dest += 8;

        } else {

            output_pixel(&dest[3], av_clip_uintp2(R_B + Y2, 30) >> 14);

            output_pixel(&dest[4], av_clip_uintp2(  G + Y2, 30) >> 14);

            output_pixel(&dest[5], av_clip_uintp2(B_R + Y2, 30) >> 14);

            dest += 6;

        }

    }

}

```

### Demonstration

```c

yuv2rgba64_2_c_template(SwsContext *c, const int32_t *buf[2],

                       const int32_t *ubuf[2], const int32_t *vbuf[2],

                       const int32_t *abuf[2], uint16_t *dest, int dstW,

                       int yalpha, int uvalpha, int y,

                       enum AVPixelFormat target, int hasAlpha)

{

    const int32_t *buf0  = buf[0],  *buf1  = buf[1],

                  *ubuf0 = ubuf[0], *ubuf1 = ubuf[1],

                  *vbuf0 = vbuf[0], *vbuf1 = vbuf[1],

                  *abuf0 = hasAlpha ? abuf[0] : NULL,

                  *abuf1 = hasAlpha ? abuf[1] : NULL;

    int  yalpha1 = 4096 - yalpha;

    int uvalpha1 = 4096 - uvalpha;

    int i;



    for (i = 0; i < ((dstW + 1) >> 1); i++) {

        int Y1 = (buf0[i * 2]     * yalpha1  + buf1[i * 2]     * yalpha) >> 14;

        int Y2 = (buf0[i * 2 + 1] * yalpha1  + buf1[i * 2 + 1] * yalpha) >> 14;

        int U  = (ubuf0[i]        * uvalpha1 + ubuf1[i]        * uvalpha + (-128 << 23)) >> 14;

        int V  = (vbuf0[i]        * uvalpha1 + vbuf1[i]        * uvalpha + (-128 << 23)) >> 14;

        int A1, A2;

        int R, G, B;



        Y1 -= c->yuv2rgb_y_offset;

        Y2 -= c->yuv2rgb_y_offset;

        Y1 *= c->yuv2rgb_y_coeff;

        Y2 *= c->yuv2rgb_y_coeff;

        Y1 += 1 << 13;

        Y2 += 1 << 13;



        R = V * c->yuv2rgb_v2r_coeff;

        G = V * c->yuv2rgb_v2g_coeff + U * c->yuv2rgb_u2g_coeff;

        B =                            U * c->yuv2rgb_u2b_coeff;



        if (hasAlpha) {

            A1 = (abuf0[i * 2    ] * yalpha1 + abuf1[i * 2    ] * yalpha) >> 1;

            A2 = (abuf0[i * 2 + 1] * yalpha1 + abuf1[i * 2 + 1] * yalpha) >> 1;



            A1 += 1 << 13;

            A2 += 1 << 13;

        }



        output_pixel(&dest[0], av_clip_uintp2(B_R + Y1, 30) >> 14);

        output_pixel(&dest[1], av_clip_uintp2(  G + Y1, 30) >> 14);

        output_pixel(&dest[2], av_clip_uintp2(R_B + Y1, 30) >> 14);

        output_pixel(&dest[3], av_clip_uintp2(A1      , 30) >> 14);

        output_pixel(&dest[4], av_clip_uintp2(B_R + Y2, 30) >> 14);

        output_pixel(&dest[5], av_clip_uintp2(  G + Y2, 30) >> 14);

        output_pixel(&dest[6], av_clip_uintp2(R_B + Y2, 30) >> 14);

        output_pixel(&dest[7], av_clip_uintp2(A2      , 30) >> 14);

        dest += 8;

    }

}

```

## H2R-070

### Query

```c

static int count_paired_channels(uint8_t (*layout_map)[3], int tags, int pos, int *current) {

    int num_pos_channels = 0;

    int first_cpe = 0;

    int sce_parity = 0;

    int i;

    for (i = *current; i < tags; i++) {

        if (layout_map[i][2] != pos)

            break;

        if (layout_map[i][0] == TYPE_CPE) {

            if (sce_parity) {

                if (pos == AAC_CHANNEL_FRONT || !first_cpe) {

                    sce_parity = 0;

                } else {

                    return -1;

                }

            }

            num_pos_channels += 2;

            first_cpe = 1;

        } else {

            num_pos_channels++;

            sce_parity ^= 1;

        }

    }

    if (sce_parity &&

        ((pos == AAC_CHANNEL_FRONT && first_cpe) || pos == AAC_CHANNEL_SIDE))

            return -1;

    *current = i;

    return num_pos_channels;

}

```

### Demonstration

```c

static int decode_segment(TAKDecContext *s, int8_t mode, int32_t *decoded, int len)

{

    struct CParam code;

    GetBitContext *gb = &s->gb;

    int i;



    if (!mode) {

        memset(decoded, 0, len * sizeof(*decoded));

        return 0;

    }



    if (mode > FF_ARRAY_ELEMS(xcodes))

        return AVERROR_INVALIDDATA;

    code = xcodes[mode - 1];



    for (i = 0; i < len; i++) {

        int x = get_bits_long(gb, code.init);

        if (x >= code.escape && get_bits1(gb)) {

            x |= 1 << code.init;

            if (x >= code.aescape) {

                int scale = get_unary(gb, 1, 9);

                if (scale == 9) {

                    int scale_bits = get_bits(gb, 3);

                    if (scale_bits > 0) {

                        if (scale_bits == 7) {

                            scale_bits += get_bits(gb, 5);

                            if (scale_bits > 29)

                                return AVERROR_INVALIDDATA;

                        }

                        scale = get_bits_long(gb, scale_bits) + 1;

                        x    += code.scale * scale;

                    }

                    x += code.bias;

                } else

                    x += code.scale * scale - code.escape;

            } else

                x -= code.escape;

        }

        decoded[i] = (x >> 1) ^ -(x & 1);

    }



    return 0;

}

```

## H2R-071

### Query

```c

static void smp_parse(const char *optarg)

{

    int smp, sockets = 0, threads = 0, cores = 0;

    char *endptr;

    char option[128];



    smp = strtoul(optarg, &endptr, 10);

    if (endptr != optarg) {

        if (*endptr == ',') {

            endptr++;

        }

    }

    if (get_param_value(option, 128, "sockets", endptr) != 0)

        sockets = strtoull(option, NULL, 10);

    if (get_param_value(option, 128, "cores", endptr) != 0)

        cores = strtoull(option, NULL, 10);

    if (get_param_value(option, 128, "threads", endptr) != 0)

        threads = strtoull(option, NULL, 10);

    if (get_param_value(option, 128, "maxcpus", endptr) != 0)

        max_cpus = strtoull(option, NULL, 10);



    /* compute missing values, prefer sockets over cores over threads */

    if (smp == 0 || sockets == 0) {

        sockets = sockets > 0 ? sockets : 1;

        cores = cores > 0 ? cores : 1;

        threads = threads > 0 ? threads : 1;

        if (smp == 0) {

            smp = cores * threads * sockets;

        }

    } else {

        if (cores == 0) {

            threads = threads > 0 ? threads : 1;

            cores = smp / (sockets * threads);

        } else {

            threads = smp / (cores * sockets);

        }

    }

    smp_cpus = smp;

    smp_cores = cores > 0 ? cores : 1;

    smp_threads = threads > 0 ? threads : 1;

    if (max_cpus == 0)

        max_cpus = smp_cpus;

}

```

### Demonstration

```c

static void smp_parse(QemuOpts *opts)

{

    if (opts) {



        unsigned cpus    = qemu_opt_get_number(opts, "cpus", 0);

        unsigned sockets = qemu_opt_get_number(opts, "sockets", 0);

        unsigned cores   = qemu_opt_get_number(opts, "cores", 0);

        unsigned threads = qemu_opt_get_number(opts, "threads", 0);



        /* compute missing values, prefer sockets over cores over threads */

        if (cpus == 0 || sockets == 0) {

            sockets = sockets > 0 ? sockets : 1;

            cores = cores > 0 ? cores : 1;

            threads = threads > 0 ? threads : 1;

            if (cpus == 0) {

                cpus = cores * threads * sockets;

            }

        } else if (cores == 0) {

            threads = threads > 0 ? threads : 1;

            cores = cpus / (sockets * threads);

        } else if (threads == 0) {

            threads = cpus / (cores * sockets);

        } else if (sockets * cores * threads < cpus) {

            error_report("cpu topology: "

                         "sockets (%u) * cores (%u) * threads (%u) < "

                         "smp_cpus (%u)",

                         sockets, cores, threads, cpus);

            exit(1);

        }



        max_cpus = qemu_opt_get_number(opts, "maxcpus", cpus);

        if (sockets * cores * threads > max_cpus) {

            error_report("cpu topology: "

                         "sockets (%u) * cores (%u) * threads (%u) > "

                         "maxcpus (%u)",

                         sockets, cores, threads, max_cpus);

            exit(1);

        }



        smp_cpus = cpus;

        smp_cores = cores > 0 ? cores : 1;

        smp_threads = threads > 0 ? threads : 1;



    }



    if (max_cpus == 0) {

        max_cpus = smp_cpus;

    }



    if (max_cpus > MAX_CPUMASK_BITS) {

        error_report("unsupported number of maxcpus");

        exit(1);

    }

    if (max_cpus < smp_cpus) {

        error_report("maxcpus must be equal to or greater than smp");

        exit(1);

    }



    if (smp_cpus > 1 || smp_cores > 1 || smp_threads > 1) {

        Error *blocker = NULL;

        error_setg(&blocker, QERR_REPLAY_NOT_SUPPORTED, "smp");

        replay_add_blocker(blocker);

    }

}

```

## H2R-072

### Query

```c

static int img_read_packet(AVFormatContext *s1, AVPacket *pkt)

{

    VideoData *s = s1->priv_data;

    char filename[1024];

    int ret;

    ByteIOContext f1, *f;



    if (get_frame_filename(filename, sizeof(filename),

                           s->path, s->img_number) < 0)

        return -EIO;

    

    if (!s->is_pipe) {

        f = &f1;

        if (url_fopen(f, filename, URL_RDONLY) < 0)

            return -EIO;

    } else {

        f = &s1->pb;

        if (url_feof(f))

            return -EIO;

    }



    av_new_packet(pkt, s->img_size);

    pkt->stream_index = 0;



    switch(s->img_fmt) {

    case IMGFMT_PGMYUV:

        ret = pgm_read(s, f, pkt->data, pkt->size, 1);

        break;

    case IMGFMT_PGM:

        ret = pgm_read(s, f, pkt->data, pkt->size, 0);

        break;

    case IMGFMT_YUV:

        ret = yuv_read(s, filename, pkt->data, pkt->size);

        break;

    case IMGFMT_PPM:

        ret = ppm_read(s, f, pkt->data, pkt->size);

        break;

    default:

        return -EIO;

    }

    

    if (!s->is_pipe) {

        url_fclose(f);

    }



    if (ret < 0) {

        av_free_packet(pkt);

        return -EIO; /* signal EOF */

    } else {

        s->img_number++;

        return 0;

    }

}

```

### Demonstration

```c

static int img_read_packet(AVFormatContext *s1, AVPacket *pkt)

{

    VideoData *s = s1->priv_data;

    char filename[1024];

    int ret;

    ByteIOContext f1, *f;



    if (!s->is_pipe) {

        if (get_frame_filename(filename, sizeof(filename),

                               s->path, s->img_number) < 0)

            return -EIO;

        f = &f1;

        if (url_fopen(f, filename, URL_RDONLY) < 0)

            return -EIO;

    } else {

        f = &s1->pb;

        if (url_feof(f))

            return -EIO;

    }



    av_new_packet(pkt, s->img_size);

    pkt->stream_index = 0;



    s->ptr = pkt->data;

    ret = av_read_image(f, filename, s->img_fmt, read_packet_alloc_cb, s);

    if (!s->is_pipe) {

        url_fclose(f);

    }



    if (ret < 0) {

        av_free_packet(pkt);

        return -EIO; /* signal EOF */

    } else {

        pkt->pts = av_rescale((int64_t)s->img_number * s1->streams[0]->codec.frame_rate_base, s1->pts_den, s1->streams[0]->codec.frame_rate) / s1->pts_num;

        s->img_number++;

        return 0;

    }

}

```

## H2R-073

### Query

```c

static inline void RENAME(bgr24ToY)(uint8_t *dst, uint8_t *src, long width)

{

#ifdef HAVE_MMX

	asm volatile(

		"mov %2, %%"REG_a"		\n\t"

		"movq "MANGLE(bgr2YCoeff)", %%mm6		\n\t"

		"movq "MANGLE(w1111)", %%mm5		\n\t"

		"pxor %%mm7, %%mm7		\n\t"

		"lea (%%"REG_a", %%"REG_a", 2), %%"REG_d"\n\t"

		ASMALIGN(4)

		"1:				\n\t"

		PREFETCH" 64(%0, %%"REG_d")	\n\t"

		"movd (%0, %%"REG_d"), %%mm0	\n\t"

		"movd 3(%0, %%"REG_d"), %%mm1	\n\t"

		"punpcklbw %%mm7, %%mm0		\n\t"

		"punpcklbw %%mm7, %%mm1		\n\t"

		"movd 6(%0, %%"REG_d"), %%mm2	\n\t"

		"movd 9(%0, %%"REG_d"), %%mm3	\n\t"

		"punpcklbw %%mm7, %%mm2		\n\t"

		"punpcklbw %%mm7, %%mm3		\n\t"

		"pmaddwd %%mm6, %%mm0		\n\t"

		"pmaddwd %%mm6, %%mm1		\n\t"

		"pmaddwd %%mm6, %%mm2		\n\t"

		"pmaddwd %%mm6, %%mm3		\n\t"

#ifndef FAST_BGR2YV12

		"psrad $8, %%mm0		\n\t"

		"psrad $8, %%mm1		\n\t"

		"psrad $8, %%mm2		\n\t"

		"psrad $8, %%mm3		\n\t"

#endif

		"packssdw %%mm1, %%mm0		\n\t"

		"packssdw %%mm3, %%mm2		\n\t"

		"pmaddwd %%mm5, %%mm0		\n\t"

		"pmaddwd %%mm5, %%mm2		\n\t"

		"packssdw %%mm2, %%mm0		\n\t"

		"psraw $7, %%mm0		\n\t"



		"movd 12(%0, %%"REG_d"), %%mm4	\n\t"

		"movd 15(%0, %%"REG_d"), %%mm1	\n\t"

		"punpcklbw %%mm7, %%mm4		\n\t"

		"punpcklbw %%mm7, %%mm1		\n\t"

		"movd 18(%0, %%"REG_d"), %%mm2	\n\t"

		"movd 21(%0, %%"REG_d"), %%mm3	\n\t"

		"punpcklbw %%mm7, %%mm2		\n\t"

		"punpcklbw %%mm7, %%mm3		\n\t"

		"pmaddwd %%mm6, %%mm4		\n\t"

		"pmaddwd %%mm6, %%mm1		\n\t"

		"pmaddwd %%mm6, %%mm2		\n\t"

		"pmaddwd %%mm6, %%mm3		\n\t"

#ifndef FAST_BGR2YV12

		"psrad $8, %%mm4		\n\t"

		"psrad $8, %%mm1		\n\t"

		"psrad $8, %%mm2		\n\t"

		"psrad $8, %%mm3		\n\t"

#endif

		"packssdw %%mm1, %%mm4		\n\t"

		"packssdw %%mm3, %%mm2		\n\t"

		"pmaddwd %%mm5, %%mm4		\n\t"

		"pmaddwd %%mm5, %%mm2		\n\t"

		"add $24, %%"REG_d"		\n\t"

		"packssdw %%mm2, %%mm4		\n\t"

		"psraw $7, %%mm4		\n\t"



		"packuswb %%mm4, %%mm0		\n\t"

		"paddusb "MANGLE(bgr2YOffset)", %%mm0	\n\t"



		"movq %%mm0, (%1, %%"REG_a")	\n\t"

		"add $8, %%"REG_a"		\n\t"

		" js 1b				\n\t"

		: : "r" (src+width*3), "r" (dst+width), "g" (-width)

		: "%"REG_a, "%"REG_d

	);

#else

	int i;

	for(i=0; i<width; i++)

	{

		int b= src[i*3+0];

		int g= src[i*3+1];

		int r= src[i*3+2];



		dst[i]= ((RY*r + GY*g + BY*b + (33<<(RGB2YUV_SHIFT-1)) )>>RGB2YUV_SHIFT);

	}

#endif

}

```

### Demonstration

```c

static inline void RENAME(bgr24ToY)(uint8_t *dst, uint8_t *src, long width)

{

#ifdef HAVE_MMX

	asm volatile(

		"mov %2, %%"REG_a"		\n\t"

		"movq "MANGLE(bgr2YCoeff)", %%mm6		\n\t"

		"movq "MANGLE(w1111)", %%mm5		\n\t"

		"pxor %%mm7, %%mm7		\n\t"

		"lea (%%"REG_a", %%"REG_a", 2), %%"REG_b"\n\t"

		ASMALIGN16

		"1:				\n\t"

		PREFETCH" 64(%0, %%"REG_b")	\n\t"

		"movd (%0, %%"REG_b"), %%mm0	\n\t"

		"movd 3(%0, %%"REG_b"), %%mm1	\n\t"

		"punpcklbw %%mm7, %%mm0		\n\t"

		"punpcklbw %%mm7, %%mm1		\n\t"

		"movd 6(%0, %%"REG_b"), %%mm2	\n\t"

		"movd 9(%0, %%"REG_b"), %%mm3	\n\t"

		"punpcklbw %%mm7, %%mm2		\n\t"

		"punpcklbw %%mm7, %%mm3		\n\t"

		"pmaddwd %%mm6, %%mm0		\n\t"

		"pmaddwd %%mm6, %%mm1		\n\t"

		"pmaddwd %%mm6, %%mm2		\n\t"

		"pmaddwd %%mm6, %%mm3		\n\t"

#ifndef FAST_BGR2YV12

		"psrad $8, %%mm0		\n\t"

		"psrad $8, %%mm1		\n\t"

		"psrad $8, %%mm2		\n\t"

		"psrad $8, %%mm3		\n\t"

#endif

		"packssdw %%mm1, %%mm0		\n\t"

		"packssdw %%mm3, %%mm2		\n\t"

		"pmaddwd %%mm5, %%mm0		\n\t"

		"pmaddwd %%mm5, %%mm2		\n\t"

		"packssdw %%mm2, %%mm0		\n\t"

		"psraw $7, %%mm0		\n\t"



		"movd 12(%0, %%"REG_b"), %%mm4	\n\t"

		"movd 15(%0, %%"REG_b"), %%mm1	\n\t"

		"punpcklbw %%mm7, %%mm4		\n\t"

		"punpcklbw %%mm7, %%mm1		\n\t"

		"movd 18(%0, %%"REG_b"), %%mm2	\n\t"

		"movd 21(%0, %%"REG_b"), %%mm3	\n\t"

		"punpcklbw %%mm7, %%mm2		\n\t"

		"punpcklbw %%mm7, %%mm3		\n\t"

		"pmaddwd %%mm6, %%mm4		\n\t"

		"pmaddwd %%mm6, %%mm1		\n\t"

		"pmaddwd %%mm6, %%mm2		\n\t"

		"pmaddwd %%mm6, %%mm3		\n\t"

#ifndef FAST_BGR2YV12

		"psrad $8, %%mm4		\n\t"

		"psrad $8, %%mm1		\n\t"

		"psrad $8, %%mm2		\n\t"

		"psrad $8, %%mm3		\n\t"

#endif

		"packssdw %%mm1, %%mm4		\n\t"

		"packssdw %%mm3, %%mm2		\n\t"

		"pmaddwd %%mm5, %%mm4		\n\t"

		"pmaddwd %%mm5, %%mm2		\n\t"

		"add $24, %%"REG_b"		\n\t"

		"packssdw %%mm2, %%mm4		\n\t"

		"psraw $7, %%mm4		\n\t"



		"packuswb %%mm4, %%mm0		\n\t"

		"paddusb "MANGLE(bgr2YOffset)", %%mm0	\n\t"



		"movq %%mm0, (%1, %%"REG_a")	\n\t"

		"add $8, %%"REG_a"		\n\t"

		" js 1b				\n\t"

		: : "r" (src+width*3), "r" (dst+width), "g" (-width)

		: "%"REG_a, "%"REG_b

	);

#else

	int i;

	for(i=0; i<width; i++)

	{

		int b= src[i*3+0];

		int g= src[i*3+1];

		int r= src[i*3+2];



		dst[i]= ((RY*r + GY*g + BY*b + (33<<(RGB2YUV_SHIFT-1)) )>>RGB2YUV_SHIFT);

	}

#endif

}

```

## H2R-074

### Query

```c

static uint64_t omap_pin_cfg_read(void *opaque, target_phys_addr_t addr,

                                  unsigned size)

{

    struct omap_mpu_state_s *s = (struct omap_mpu_state_s *) opaque;



    if (size != 4) {

        return omap_badwidth_read32(opaque, addr);

    }



    switch (addr) {

    case 0x00:	/* FUNC_MUX_CTRL_0 */

    case 0x04:	/* FUNC_MUX_CTRL_1 */

    case 0x08:	/* FUNC_MUX_CTRL_2 */

        return s->func_mux_ctrl[addr >> 2];



    case 0x0c:	/* COMP_MODE_CTRL_0 */

        return s->comp_mode_ctrl[0];



    case 0x10:	/* FUNC_MUX_CTRL_3 */

    case 0x14:	/* FUNC_MUX_CTRL_4 */

    case 0x18:	/* FUNC_MUX_CTRL_5 */

    case 0x1c:	/* FUNC_MUX_CTRL_6 */

    case 0x20:	/* FUNC_MUX_CTRL_7 */

    case 0x24:	/* FUNC_MUX_CTRL_8 */

    case 0x28:	/* FUNC_MUX_CTRL_9 */

    case 0x2c:	/* FUNC_MUX_CTRL_A */

    case 0x30:	/* FUNC_MUX_CTRL_B */

    case 0x34:	/* FUNC_MUX_CTRL_C */

    case 0x38:	/* FUNC_MUX_CTRL_D */

        return s->func_mux_ctrl[(addr >> 2) - 1];



    case 0x40:	/* PULL_DWN_CTRL_0 */

    case 0x44:	/* PULL_DWN_CTRL_1 */

    case 0x48:	/* PULL_DWN_CTRL_2 */

    case 0x4c:	/* PULL_DWN_CTRL_3 */

        return s->pull_dwn_ctrl[(addr & 0xf) >> 2];



    case 0x50:	/* GATE_INH_CTRL_0 */

        return s->gate_inh_ctrl[0];



    case 0x60:	/* VOLTAGE_CTRL_0 */

        return s->voltage_ctrl[0];



    case 0x70:	/* TEST_DBG_CTRL_0 */

        return s->test_dbg_ctrl[0];



    case 0x80:	/* MOD_CONF_CTRL_0 */

        return s->mod_conf_ctrl[0];

    }



    OMAP_BAD_REG(addr);

    return 0;

}

```

### Demonstration

```c

static uint64_t omap_tcmi_read(void *opaque, target_phys_addr_t addr,

                               unsigned size)

{

    struct omap_mpu_state_s *s = (struct omap_mpu_state_s *) opaque;

    uint32_t ret;



    if (size != 4) {

        return omap_badwidth_read32(opaque, addr);

    }



    switch (addr) {

    case 0x00:	/* IMIF_PRIO */

    case 0x04:	/* EMIFS_PRIO */

    case 0x08:	/* EMIFF_PRIO */

    case 0x0c:	/* EMIFS_CONFIG */

    case 0x10:	/* EMIFS_CS0_CONFIG */

    case 0x14:	/* EMIFS_CS1_CONFIG */

    case 0x18:	/* EMIFS_CS2_CONFIG */

    case 0x1c:	/* EMIFS_CS3_CONFIG */

    case 0x24:	/* EMIFF_MRS */

    case 0x28:	/* TIMEOUT1 */

    case 0x2c:	/* TIMEOUT2 */

    case 0x30:	/* TIMEOUT3 */

    case 0x3c:	/* EMIFF_SDRAM_CONFIG_2 */

    case 0x40:	/* EMIFS_CFG_DYN_WAIT */

        return s->tcmi_regs[addr >> 2];



    case 0x20:	/* EMIFF_SDRAM_CONFIG */

        ret = s->tcmi_regs[addr >> 2];

        s->tcmi_regs[addr >> 2] &= ~1; /* XXX: Clear SLRF on SDRAM access */

        /* XXX: We can try using the VGA_DIRTY flag for this */

        return ret;

    }



    OMAP_BAD_REG(addr);

    return 0;

}

```

## H2R-075

### Query

```c

int qemu_devtree_setprop(void *fdt, const char *node_path,

                         const char *property, void *val_array, int size)

{

    int offset;



    offset = fdt_path_offset(fdt, node_path);

    if (offset < 0)

        return offset;



    return fdt_setprop(fdt, offset, property, val_array, size);

}

```

### Demonstration

```c

int qemu_devtree_setprop_cell(void *fdt, const char *node_path,

                              const char *property, uint32_t val)

{

    int offset;



    offset = fdt_path_offset(fdt, node_path);

    if (offset < 0)

        return offset;



    return fdt_setprop_cell(fdt, offset, property, val);

}

```

## H2R-076

### Query

```c

static inline void RENAME(rgb2rgb_init)(void)

{

#if !COMPILE_TEMPLATE_SSE2

#if !COMPILE_TEMPLATE_AMD3DNOW

    rgb15to16          = RENAME(rgb15to16);

    rgb15tobgr24       = RENAME(rgb15tobgr24);

    rgb15to32          = RENAME(rgb15to32);

    rgb16tobgr24       = RENAME(rgb16tobgr24);

    rgb16to32          = RENAME(rgb16to32);

    rgb16to15          = RENAME(rgb16to15);

    rgb24tobgr16       = RENAME(rgb24tobgr16);

    rgb24tobgr15       = RENAME(rgb24tobgr15);

    rgb24tobgr32       = RENAME(rgb24tobgr32);

    rgb32to16          = RENAME(rgb32to16);

    rgb32to15          = RENAME(rgb32to15);

    rgb32tobgr24       = RENAME(rgb32tobgr24);

    rgb24to15          = RENAME(rgb24to15);

    rgb24to16          = RENAME(rgb24to16);

    rgb24tobgr24       = RENAME(rgb24tobgr24);

    shuffle_bytes_2103 = RENAME(shuffle_bytes_2103);

    rgb32tobgr16       = RENAME(rgb32tobgr16);

    rgb32tobgr15       = RENAME(rgb32tobgr15);

    yv12toyuy2         = RENAME(yv12toyuy2);

    yv12touyvy         = RENAME(yv12touyvy);

    yuv422ptoyuy2      = RENAME(yuv422ptoyuy2);

    yuv422ptouyvy      = RENAME(yuv422ptouyvy);

    yuy2toyv12         = RENAME(yuy2toyv12);

    vu9_to_vu12        = RENAME(vu9_to_vu12);

    yvu9_to_yuy2       = RENAME(yvu9_to_yuy2);

    uyvytoyuv422       = RENAME(uyvytoyuv422);

    yuyvtoyuv422       = RENAME(yuyvtoyuv422);

#endif /* !COMPILE_TEMPLATE_AMD3DNOW */



#if COMPILE_TEMPLATE_MMXEXT || COMPILE_TEMPLATE_AMD3DNOW

    planar2x           = RENAME(planar2x);

#endif /* COMPILE_TEMPLATE_MMXEXT || COMPILE_TEMPLATE_AMD3DNOW */

    rgb24toyv12        = RENAME(rgb24toyv12);



    yuyvtoyuv420       = RENAME(yuyvtoyuv420);

    uyvytoyuv420       = RENAME(uyvytoyuv420);

#endif /* !COMPILE_TEMPLATE_SSE2 */



#if !COMPILE_TEMPLATE_AMD3DNOW

    interleaveBytes    = RENAME(interleaveBytes);

#endif /* !COMPILE_TEMPLATE_AMD3DNOW */

}

```

### Demonstration

```c

static inline void RENAME(rgb2rgb_init)(void)

{

    rgb15to16       = RENAME(rgb15to16);

    rgb15tobgr24    = RENAME(rgb15tobgr24);

    rgb15to32       = RENAME(rgb15to32);

    rgb16tobgr24    = RENAME(rgb16tobgr24);

    rgb16to32       = RENAME(rgb16to32);

    rgb16to15       = RENAME(rgb16to15);

    rgb24tobgr16    = RENAME(rgb24tobgr16);

    rgb24tobgr15    = RENAME(rgb24tobgr15);

    rgb24tobgr32    = RENAME(rgb24tobgr32);

    rgb32to16       = RENAME(rgb32to16);

    rgb32to15       = RENAME(rgb32to15);

    rgb32tobgr24    = RENAME(rgb32tobgr24);

    rgb24to15       = RENAME(rgb24to15);

    rgb24to16       = RENAME(rgb24to16);

    rgb24tobgr24    = RENAME(rgb24tobgr24);

    shuffle_bytes_2103 = RENAME(shuffle_bytes_2103);

    rgb32tobgr16    = RENAME(rgb32tobgr16);

    rgb32tobgr15    = RENAME(rgb32tobgr15);

    yv12toyuy2      = RENAME(yv12toyuy2);

    yv12touyvy      = RENAME(yv12touyvy);

    yuv422ptoyuy2   = RENAME(yuv422ptoyuy2);

    yuv422ptouyvy   = RENAME(yuv422ptouyvy);

    yuy2toyv12      = RENAME(yuy2toyv12);

    planar2x        = RENAME(planar2x);

    rgb24toyv12     = RENAME(rgb24toyv12);

    interleaveBytes = RENAME(interleaveBytes);

    vu9_to_vu12     = RENAME(vu9_to_vu12);

    yvu9_to_yuy2    = RENAME(yvu9_to_yuy2);



    uyvytoyuv420    = RENAME(uyvytoyuv420);

    uyvytoyuv422    = RENAME(uyvytoyuv422);

    yuyvtoyuv420    = RENAME(yuyvtoyuv420);

    yuyvtoyuv422    = RENAME(yuyvtoyuv422);

}

```

## H2R-077

### Query

```c

static void musb_rx_req(MUSBState *s, int epnum)

{

    MUSBEndPoint *ep = s->ep + epnum;

    int total;



    /* If we already have a packet, which didn't fit into the

     * 64 bytes of the FIFO, only move the FIFO start and return. (Obsolete) */

    if (ep->packey[1].p.pid == USB_TOKEN_IN && ep->status[1] >= 0 &&

                    (ep->fifostart[1]) + ep->rxcount <

                    ep->packey[1].p.len) {

        TRACE("0x%08x, %d",  ep->fifostart[1], ep->rxcount );

        ep->fifostart[1] += ep->rxcount;

        ep->fifolen[1] = 0;



        ep->rxcount = MIN(ep->packey[0].p.len - (ep->fifostart[1]),

                        ep->maxp[1]);



        ep->csr[1] &= ~MGC_M_RXCSR_H_REQPKT;

        if (!epnum)

            ep->csr[0] &= ~MGC_M_CSR0_H_REQPKT;



        /* Clear all of the error bits first */

        ep->csr[1] &= ~(MGC_M_RXCSR_H_ERROR | MGC_M_RXCSR_H_RXSTALL |

                        MGC_M_RXCSR_DATAERROR);

        if (!epnum)

            ep->csr[0] &= ~(MGC_M_CSR0_H_ERROR | MGC_M_CSR0_H_RXSTALL |

                            MGC_M_CSR0_H_NAKTIMEOUT | MGC_M_CSR0_H_NO_PING);



        ep->csr[1] |= MGC_M_RXCSR_FIFOFULL | MGC_M_RXCSR_RXPKTRDY;

        if (!epnum)

            ep->csr[0] |= MGC_M_CSR0_RXPKTRDY;

        musb_rx_intr_set(s, epnum, 1);

        return;

    }



    /* The driver sets maxp[1] to 64 or less because it knows the hardware

     * FIFO is this deep.  Bigger packets get split in

     * usb_generic_handle_packet but we can also do the splitting locally

     * for performance.  It turns out we can also have a bigger FIFO and

     * ignore the limit set in ep->maxp[1].  The Linux MUSB driver deals

     * OK with single packets of even 32KB and we avoid splitting, however

     * usb_msd.c sometimes sends a packet bigger than what Linux expects

     * (e.g. 8192 bytes instead of 4096) and we get an OVERRUN.  Splitting

     * hides this overrun from Linux.  Up to 4096 everything is fine

     * though.  Currently this is disabled.

     *

     * XXX: mind ep->fifosize.  */

    total = MIN(ep->maxp[1] & 0x3ff, sizeof(s->buf));



#ifdef SETUPLEN_HACK

    /* Why should *we* do that instead of Linux?  */

    if (!epnum) {

        if (ep->packey[0].p.devaddr == 2) {

            total = MIN(s->setup_len, 8);

        } else {

            total = MIN(s->setup_len, 64);

        }

        s->setup_len -= total;

    }

#endif



    return musb_packet(s, ep, epnum, USB_TOKEN_IN,

                    total, musb_rx_packet_complete, 1);

}

```

### Demonstration

```c

static int usbredir_handle_iso_data(USBRedirDevice *dev, USBPacket *p,

                                     uint8_t ep)

{

    int status, len;



    if (!dev->endpoint[EP2I(ep)].iso_started &&

            !dev->endpoint[EP2I(ep)].iso_error) {

        struct usb_redir_start_iso_stream_header start_iso = {

            .endpoint = ep,

            /* TODO maybe do something with these depending on ep interval? */

            .pkts_per_urb = 32,

            .no_urbs = 3,

        };

        /* No id, we look at the ep when receiving a status back */

        usbredirparser_send_start_iso_stream(dev->parser, 0, &start_iso);

        usbredirparser_do_write(dev->parser);

        DPRINTF("iso stream started ep %02X\n", ep);

        dev->endpoint[EP2I(ep)].iso_started = 1;

    }



    if (ep & USB_DIR_IN) {

        struct buf_packet *isop;



        isop = QTAILQ_FIRST(&dev->endpoint[EP2I(ep)].bufpq);

        if (isop == NULL) {

            DPRINTF2("iso-token-in ep %02X, no isop\n", ep);

            /* Check iso_error for stream errors, otherwise its an underrun */

            status = dev->endpoint[EP2I(ep)].iso_error;

            dev->endpoint[EP2I(ep)].iso_error = 0;

            return usbredir_handle_status(dev, status, 0);

        }

        DPRINTF2("iso-token-in ep %02X status %d len %d\n", ep, isop->status,

                 isop->len);



        status = isop->status;

        if (status != usb_redir_success) {

            bufp_free(dev, isop, ep);

            return usbredir_handle_status(dev, status, 0);

        }



        len = isop->len;

        if (len > p->len) {

            ERROR("received iso data is larger then packet ep %02X\n", ep);

            bufp_free(dev, isop, ep);

            return USB_RET_NAK;

        }

        memcpy(p->data, isop->data, len);

        bufp_free(dev, isop, ep);

        return len;

    } else {

        /* If the stream was not started because of a pending error don't

           send the packet to the usb-host */

        if (dev->endpoint[EP2I(ep)].iso_started) {

            struct usb_redir_iso_packet_header iso_packet = {

                .endpoint = ep,

                .length = p->len

            };

            /* No id, we look at the ep when receiving a status back */

            usbredirparser_send_iso_packet(dev->parser, 0, &iso_packet,

                                           p->data, p->len);

            usbredirparser_do_write(dev->parser);

        }

        status = dev->endpoint[EP2I(ep)].iso_error;

        dev->endpoint[EP2I(ep)].iso_error = 0;

        DPRINTF2("iso-token-out ep %02X status %d len %d\n", ep, status,

                 p->len);

        return usbredir_handle_status(dev, status, p->len);

    }

}

```

## H2R-078

### Query

```c

static void ehci_mem_writew(void *ptr, target_phys_addr_t addr, uint32_t val)

{

    fprintf(stderr, "EHCI doesn't handle 16-bit writes to MMIO\n");

    exit(1);

}

```

### Demonstration

```c

static void ehci_mem_writeb(void *ptr, target_phys_addr_t addr, uint32_t val)

{

    fprintf(stderr, "EHCI doesn't handle byte writes to MMIO\n");

    exit(1);

}

```

## H2R-079

### Query

```c

int av_seek_frame(AVFormatContext *s, int stream_index, int64_t timestamp, int flags)

{

    int ret;

    AVStream *st;



    ff_read_frame_flush(s);



    if(flags & AVSEEK_FLAG_BYTE)

        return av_seek_frame_byte(s, stream_index, timestamp, flags);



    if(stream_index < 0){

        stream_index= av_find_default_stream_index(s);

        if(stream_index < 0)

            return -1;



        st= s->streams[stream_index];

       /* timestamp for default must be expressed in AV_TIME_BASE units */

        timestamp = av_rescale(timestamp, st->time_base.den, AV_TIME_BASE * (int64_t)st->time_base.num);

    }



    /* first, we try the format specific seek */

    if (s->iformat->read_seek)

        ret = s->iformat->read_seek(s, stream_index, timestamp, flags);

    else

        ret = -1;

    if (ret >= 0) {

        return 0;

    }



    if(s->iformat->read_timestamp)

        return av_seek_frame_binary(s, stream_index, timestamp, flags);

    else

        return av_seek_frame_generic(s, stream_index, timestamp, flags);

}

```

### Demonstration

```c

int av_seek_frame(AVFormatContext *s, int stream_index, int64_t timestamp, int flags)

{

    int ret;

    AVStream *st;



    ff_read_frame_flush(s);



    if(flags & AVSEEK_FLAG_BYTE)

        return seek_frame_byte(s, stream_index, timestamp, flags);



    if(stream_index < 0){

        stream_index= av_find_default_stream_index(s);

        if(stream_index < 0)

            return -1;



        st= s->streams[stream_index];

        /* timestamp for default must be expressed in AV_TIME_BASE units */

        timestamp = av_rescale(timestamp, st->time_base.den, AV_TIME_BASE * (int64_t)st->time_base.num);

    }



    /* first, we try the format specific seek */

    if (s->iformat->read_seek)

        ret = s->iformat->read_seek(s, stream_index, timestamp, flags);

    else

        ret = -1;

    if (ret >= 0) {

        return 0;

    }



    if(s->iformat->read_timestamp && !(s->iformat->flags & AVFMT_NOBINSEARCH))

        return av_seek_frame_binary(s, stream_index, timestamp, flags);

    else if (!(s->iformat->flags & AVFMT_NOGENSEARCH))

        return seek_frame_generic(s, stream_index, timestamp, flags);

    else

        return -1;

}

```

## H2R-080

### Query

```c

static inline void mix_2f_1r_to_dolby(AC3DecodeContext *ctx)

{

    int i;

    float (*output)[256] = ctx->audio_block.block_output;



    for (i = 0; i < 256; i++) {

        output[1][i] -= output[3][i];

        output[2][i] += output[3][i];

    }

    memset(output[3], 0, sizeof(output[3]));

}

```

### Demonstration

```c

static inline void mix_2f_1r_to_stereo(AC3DecodeContext *ctx)

{

    int i;

    float (*output)[256] = ctx->audio_block.block_output;



    for (i = 0; i < 256; i++) {

        output[1][i] += output[2][i];

        output[2][i] += output[3][i];

    }

    memset(output[3], 0, sizeof(output[3]));

}

```

## H2R-081

### Query

```c

static int mp_pacl_removexattr(FsContext *ctx,

                               const char *path, const char *name)

{

    int ret;

    char *buffer;



    buffer = rpath(ctx, path);

    ret  = lremovexattr(buffer, MAP_ACL_ACCESS);

    if (ret == -1 && errno == ENODATA) {

        /*

         * We don't get ENODATA error when trying to remove a

         * posix acl that is not present. So don't throw the error

         * even in case of mapped security model

         */

        errno = 0;

        ret = 0;

    }

    g_free(buffer);

    return ret;

}

```

### Demonstration

```c

static int mp_dacl_removexattr(FsContext *ctx,

                               const char *path, const char *name)

{

    int ret;

    char *buffer;



    buffer = rpath(ctx, path);

    ret  = lremovexattr(buffer, MAP_ACL_DEFAULT);

    if (ret == -1 && errno == ENODATA) {

        /*

         * We don't get ENODATA error when trying to remove a

         * posix acl that is not present. So don't throw the error

         * even in case of mapped security model

         */

        errno = 0;

        ret = 0;

    }

    g_free(buffer);

    return ret;

}

```

## H2R-082

### Query

```c

static int bit8x8_c(MpegEncContext *s, uint8_t *src1, uint8_t *src2,

                    ptrdiff_t stride, int h)

{

    const uint8_t *scantable = s->intra_scantable.permutated;

    LOCAL_ALIGNED_16(int16_t, temp, [64]);

    int i, last, run, bits, level, start_i;

    const int esc_length = s->ac_esc_length;

    uint8_t *length, *last_length;



    av_assert2(h == 8);



    s->pdsp.diff_pixels(temp, src1, src2, stride);



    s->block_last_index[0 /* FIXME */] =

    last                               =

        s->fast_dct_quantize(s, temp, 0 /* FIXME */, s->qscale, &i);



    bits = 0;



    if (s->mb_intra) {

        start_i     = 1;

        length      = s->intra_ac_vlc_length;

        last_length = s->intra_ac_vlc_last_length;

        bits       += s->luma_dc_vlc_length[temp[0] + 256]; // FIXME: chroma

    } else {

        start_i     = 0;

        length      = s->inter_ac_vlc_length;

        last_length = s->inter_ac_vlc_last_length;

    }



    if (last >= start_i) {

        run = 0;

        for (i = start_i; i < last; i++) {

            int j = scantable[i];

            level = temp[j];



            if (level) {

                level += 64;

                if ((level & (~127)) == 0)

                    bits += length[UNI_AC_ENC_INDEX(run, level)];

                else

                    bits += esc_length;

                run = 0;

            } else

                run++;

        }

        i = scantable[last];



        level = temp[i] + 64;



        av_assert2(level - 64);



        if ((level & (~127)) == 0)

            bits += last_length[UNI_AC_ENC_INDEX(run, level)];

        else

            bits += esc_length;

    }



    return bits;

}

```

### Demonstration

```c

static void vp6_parse_coeff_huffman(VP56Context *s)

{

    VP56Model *model = s->modelp;

    uint8_t *permute = s->scantable.permutated;

    VLC *vlc_coeff;

    int coeff, sign, coeff_idx;

    int b, cg, idx;

    int pt = 0;    /* plane type (0 for Y, 1 for U or V) */



    for (b=0; b<6; b++) {

        int ct = 0;    /* code type */

        if (b > 3) pt = 1;

        vlc_coeff = &s->dccv_vlc[pt];



        for (coeff_idx=0; coeff_idx<64; ) {

            int run = 1;

            if (coeff_idx<2 && s->nb_null[coeff_idx][pt]) {

                s->nb_null[coeff_idx][pt]--;

                if (coeff_idx)

                    break;

            } else {

                if (get_bits_count(&s->gb) >= s->gb.size_in_bits)

                    return;

                coeff = get_vlc2(&s->gb, vlc_coeff->table, 9, 3);

                if (coeff == 0) {

                    if (coeff_idx) {

                        int pt = (coeff_idx >= 6);

                        run += get_vlc2(&s->gb, s->runv_vlc[pt].table, 9, 3);

                        if (run >= 9)

                            run += get_bits(&s->gb, 6);

                    } else

                        s->nb_null[0][pt] = vp6_get_nb_null(s);

                    ct = 0;

                } else if (coeff == 11) {  /* end of block */

                    if (coeff_idx == 1)    /* first AC coeff ? */

                        s->nb_null[1][pt] = vp6_get_nb_null(s);

                    break;

                } else {

                    int coeff2 = vp56_coeff_bias[coeff];

                    if (coeff > 4)

                        coeff2 += get_bits(&s->gb, coeff <= 9 ? coeff - 4 : 11);

                    ct = 1 + (coeff2 > 1);

                    sign = get_bits1(&s->gb);

                    coeff2 = (coeff2 ^ -sign) + sign;

                    if (coeff_idx)

                        coeff2 *= s->dequant_ac;

                    idx = model->coeff_index_to_pos[coeff_idx];

                    s->block_coeff[b][permute[idx]] = coeff2;

                }

            }

            coeff_idx+=run;

            cg = FFMIN(vp6_coeff_groups[coeff_idx], 3);

            vlc_coeff = &s->ract_vlc[pt][ct][cg];

        }

    }

}

```

## H2R-083

### Query

```c

static int ivi_mc(ivi_mc_func mc, int16_t *buf, const int16_t *ref_buf,

                  int offs, int mv_x, int mv_y, uint32_t pitch,

                  int mc_type)

{

    int ref_offs = offs + mv_y * pitch + mv_x;



    if (offs < 0 || ref_offs < 0 || !ref_buf)

        return AVERROR_INVALIDDATA;



    mc(buf + offs, ref_buf + ref_offs, pitch, mc_type);



    return 0;

}

```

### Demonstration

```c

static int vtd_page_walk(VTDContextEntry *ce, uint64_t start, uint64_t end,

                         vtd_page_walk_hook hook_fn, void *private,

                         bool notify_unmap)

{

    dma_addr_t addr = vtd_ce_get_slpt_base(ce);

    uint32_t level = vtd_ce_get_level(ce);



    if (!vtd_iova_range_check(start, ce)) {

        return -VTD_FR_ADDR_BEYOND_MGAW;

    }



    if (!vtd_iova_range_check(end, ce)) {

        /* Fix end so that it reaches the maximum */

        end = vtd_iova_limit(ce);

    }



    return vtd_page_walk_level(addr, start, end, hook_fn, private,

                               level, true, true, notify_unmap);

}

```

## H2R-084

### Query

```c

static void monitor_readline(const char *prompt, int is_password,

                             char *buf, int buf_size)

{

    readline_start(prompt, is_password, monitor_readline_cb, NULL);

    readline_show_prompt();

    monitor_readline_buf = buf;

    monitor_readline_buf_size = buf_size;

    monitor_readline_started = 1;

    while (monitor_readline_started) {

        main_loop_wait(10);

    }

}

```

### Demonstration

```c

void monitor_readline(const char *prompt, int is_password,

                      char *buf, int buf_size)

{

    int i;



    if (is_password) {

        for (i = 0; i < MAX_MON; i++)

            if (monitor_hd[i] && monitor_hd[i]->focus == 0)

                qemu_chr_send_event(monitor_hd[i], CHR_EVENT_FOCUS);

    }

    readline_start(prompt, is_password, monitor_readline_cb, NULL);

    monitor_readline_buf = buf;

    monitor_readline_buf_size = buf_size;

    monitor_readline_started = 1;

    while (monitor_readline_started) {

        main_loop_wait(10);

    }

}

```

## H2R-085

### Query

```c

static void RENAME(vertical_compose53iL0)(uint8_t *_b0, uint8_t *_b1, uint8_t *_b2,

                                          int width)

{

    int i;

    TYPE *b0 = (TYPE *)_b0;

    TYPE *b1 = (TYPE *)_b1;

    TYPE *b2 = (TYPE *)_b2;

    for (i = 0; i < width; i++)

        b1[i] -= (b0[i] + b2[i] + 2) >> 2;

}

```

### Demonstration

```c

static void hScale16To19_c(SwsContext *c, int16_t *_dst, int dstW, const uint8_t *_src,

                           const int16_t *filter,

                           const int16_t *filterPos, int filterSize)

{

    int i;

    int32_t *dst = (int32_t *) _dst;

    const uint16_t *src = (const uint16_t *) _src;

    int bits = av_pix_fmt_descriptors[c->srcFormat].comp[0].depth_minus1;

    int sh = bits - 4;



    for (i = 0; i < dstW; i++) {

        int j;

        int srcPos = filterPos[i];

        int val = 0;



        for (j = 0; j < filterSize; j++) {

            val += src[srcPos + j] * filter[filterSize * i + j];

        }

        // filter=14 bit, input=16 bit, output=30 bit, >> 11 makes 19 bit

        dst[i] = FFMIN(val >> sh, (1 << 19) - 1);

    }

}

```

## H2R-086

### Query

```c

gen_intermediate_code_internal(MIPSCPU *cpu, TranslationBlock *tb,

                               bool search_pc)

{

    CPUState *cs = CPU(cpu);

    CPUMIPSState *env = &cpu->env;

    DisasContext ctx;

    target_ulong pc_start;

    uint16_t *gen_opc_end;

    CPUBreakpoint *bp;

    int j, lj = -1;

    int num_insns;

    int max_insns;

    int insn_bytes;

    int is_branch;



    if (search_pc)

        qemu_log("search pc %d\n", search_pc);



    pc_start = tb->pc;

    gen_opc_end = tcg_ctx.gen_opc_buf + OPC_MAX_SIZE;

    ctx.pc = pc_start;

    ctx.saved_pc = -1;

    ctx.singlestep_enabled = cs->singlestep_enabled;

    ctx.insn_flags = env->insn_flags;

    ctx.tb = tb;

    ctx.bstate = BS_NONE;

    /* Restore delay slot state from the tb context.  */

    ctx.hflags = (uint32_t)tb->flags; /* FIXME: maybe use 64 bits here? */

    restore_cpu_state(env, &ctx);

#ifdef CONFIG_USER_ONLY

        ctx.mem_idx = MIPS_HFLAG_UM;

#else

        ctx.mem_idx = ctx.hflags & MIPS_HFLAG_KSU;

#endif

    num_insns = 0;

    max_insns = tb->cflags & CF_COUNT_MASK;

    if (max_insns == 0)

        max_insns = CF_COUNT_MASK;

    LOG_DISAS("\ntb %p idx %d hflags %04x\n", tb, ctx.mem_idx, ctx.hflags);

    gen_tb_start();

    while (ctx.bstate == BS_NONE) {

        if (unlikely(!QTAILQ_EMPTY(&env->breakpoints))) {

            QTAILQ_FOREACH(bp, &env->breakpoints, entry) {

                if (bp->pc == ctx.pc) {

                    save_cpu_state(&ctx, 1);

                    ctx.bstate = BS_BRANCH;

                    gen_helper_0e0i(raise_exception, EXCP_DEBUG);

                    /* Include the breakpoint location or the tb won't

                     * be flushed when it must be.  */

                    ctx.pc += 4;

                    goto done_generating;

                }

            }

        }



        if (search_pc) {

            j = tcg_ctx.gen_opc_ptr - tcg_ctx.gen_opc_buf;

            if (lj < j) {

                lj++;

                while (lj < j)

                    tcg_ctx.gen_opc_instr_start[lj++] = 0;

            }

            tcg_ctx.gen_opc_pc[lj] = ctx.pc;

            gen_opc_hflags[lj] = ctx.hflags & MIPS_HFLAG_BMASK;

            gen_opc_btarget[lj] = ctx.btarget;

            tcg_ctx.gen_opc_instr_start[lj] = 1;

            tcg_ctx.gen_opc_icount[lj] = num_insns;

        }

        if (num_insns + 1 == max_insns && (tb->cflags & CF_LAST_IO))

            gen_io_start();



        is_branch = 0;

        if (!(ctx.hflags & MIPS_HFLAG_M16)) {

            ctx.opcode = cpu_ldl_code(env, ctx.pc);

            insn_bytes = 4;

            decode_opc(env, &ctx, &is_branch);

        } else if (ctx.insn_flags & ASE_MICROMIPS) {

            ctx.opcode = cpu_lduw_code(env, ctx.pc);

            insn_bytes = decode_micromips_opc(env, &ctx, &is_branch);

        } else if (ctx.insn_flags & ASE_MIPS16) {

            ctx.opcode = cpu_lduw_code(env, ctx.pc);

            insn_bytes = decode_mips16_opc(env, &ctx, &is_branch);

        } else {

            generate_exception(&ctx, EXCP_RI);

            ctx.bstate = BS_STOP;

            break;

        }

        if (!is_branch) {

            handle_delay_slot(&ctx, insn_bytes);

        }

        ctx.pc += insn_bytes;



        num_insns++;



        /* Execute a branch and its delay slot as a single instruction.

           This is what GDB expects and is consistent with what the

           hardware does (e.g. if a delay slot instruction faults, the

           reported PC is the PC of the branch).  */

        if (cs->singlestep_enabled && (ctx.hflags & MIPS_HFLAG_BMASK) == 0) {

            break;

        }



        if ((ctx.pc & (TARGET_PAGE_SIZE - 1)) == 0)

            break;



        if (tcg_ctx.gen_opc_ptr >= gen_opc_end) {

            break;

        }



        if (num_insns >= max_insns)

            break;



        if (singlestep)

            break;

    }

    if (tb->cflags & CF_LAST_IO) {

        gen_io_end();

    }

    if (cs->singlestep_enabled && ctx.bstate != BS_BRANCH) {

        save_cpu_state(&ctx, ctx.bstate == BS_NONE);

        gen_helper_0e0i(raise_exception, EXCP_DEBUG);

    } else {

        switch (ctx.bstate) {

        case BS_STOP:

            gen_goto_tb(&ctx, 0, ctx.pc);

            break;

        case BS_NONE:

            save_cpu_state(&ctx, 0);

            gen_goto_tb(&ctx, 0, ctx.pc);

            break;

        case BS_EXCP:

            tcg_gen_exit_tb(0);

            break;

        case BS_BRANCH:

        default:

            break;

        }

    }

done_generating:

    gen_tb_end(tb, num_insns);

    *tcg_ctx.gen_opc_ptr = INDEX_op_end;

    if (search_pc) {

        j = tcg_ctx.gen_opc_ptr - tcg_ctx.gen_opc_buf;

        lj++;

        while (lj <= j)

            tcg_ctx.gen_opc_instr_start[lj++] = 0;

    } else {

        tb->size = ctx.pc - pc_start;

        tb->icount = num_insns;

    }

#ifdef DEBUG_DISAS

    LOG_DISAS("\n");

    if (qemu_loglevel_mask(CPU_LOG_TB_IN_ASM)) {

        qemu_log("IN: %s\n", lookup_symbol(pc_start));

        log_target_disas(env, pc_start, ctx.pc - pc_start, 0);

        qemu_log("\n");

    }

#endif

}

```

### Demonstration

```c

gen_intermediate_code_internal(MIPSCPU *cpu, TranslationBlock *tb,

                               bool search_pc)

{

    CPUState *cs = CPU(cpu);

    CPUMIPSState *env = &cpu->env;

    DisasContext ctx;

    target_ulong pc_start;

    uint16_t *gen_opc_end;

    CPUBreakpoint *bp;

    int j, lj = -1;

    int num_insns;

    int max_insns;

    int insn_bytes;

    int is_slot;



    if (search_pc)

        qemu_log("search pc %d\n", search_pc);



    pc_start = tb->pc;

    gen_opc_end = tcg_ctx.gen_opc_buf + OPC_MAX_SIZE;

    ctx.pc = pc_start;

    ctx.saved_pc = -1;

    ctx.singlestep_enabled = cs->singlestep_enabled;

    ctx.insn_flags = env->insn_flags;

    ctx.CP0_Config1 = env->CP0_Config1;

    ctx.tb = tb;

    ctx.bstate = BS_NONE;

    ctx.kscrexist = (env->CP0_Config4 >> CP0C4_KScrExist) & 0xff;

    ctx.rxi = (env->CP0_Config3 >> CP0C3_RXI) & 1;

    ctx.ie = (env->CP0_Config4 >> CP0C4_IE) & 3;

    ctx.bi = (env->CP0_Config3 >> CP0C3_BI) & 1;

    ctx.bp = (env->CP0_Config3 >> CP0C3_BP) & 1;

    /* Restore delay slot state from the tb context.  */

    ctx.hflags = (uint32_t)tb->flags; /* FIXME: maybe use 64 bits here? */

    ctx.ulri = env->CP0_Config3 & (1 << CP0C3_ULRI);

    restore_cpu_state(env, &ctx);

#ifdef CONFIG_USER_ONLY

        ctx.mem_idx = MIPS_HFLAG_UM;

#else

        ctx.mem_idx = ctx.hflags & MIPS_HFLAG_KSU;

#endif

    num_insns = 0;

    max_insns = tb->cflags & CF_COUNT_MASK;

    if (max_insns == 0)

        max_insns = CF_COUNT_MASK;

    LOG_DISAS("\ntb %p idx %d hflags %04x\n", tb, ctx.mem_idx, ctx.hflags);

    gen_tb_start();

    while (ctx.bstate == BS_NONE) {

        if (unlikely(!QTAILQ_EMPTY(&cs->breakpoints))) {

            QTAILQ_FOREACH(bp, &cs->breakpoints, entry) {

                if (bp->pc == ctx.pc) {

                    save_cpu_state(&ctx, 1);

                    ctx.bstate = BS_BRANCH;

                    gen_helper_0e0i(raise_exception, EXCP_DEBUG);

                    /* Include the breakpoint location or the tb won't

                     * be flushed when it must be.  */

                    ctx.pc += 4;

                    goto done_generating;

                }

            }

        }



        if (search_pc) {

            j = tcg_ctx.gen_opc_ptr - tcg_ctx.gen_opc_buf;

            if (lj < j) {

                lj++;

                while (lj < j)

                    tcg_ctx.gen_opc_instr_start[lj++] = 0;

            }

            tcg_ctx.gen_opc_pc[lj] = ctx.pc;

            gen_opc_hflags[lj] = ctx.hflags & MIPS_HFLAG_BMASK;

            gen_opc_btarget[lj] = ctx.btarget;

            tcg_ctx.gen_opc_instr_start[lj] = 1;

            tcg_ctx.gen_opc_icount[lj] = num_insns;

        }

        if (num_insns + 1 == max_insns && (tb->cflags & CF_LAST_IO))

            gen_io_start();



        is_slot = ctx.hflags & MIPS_HFLAG_BMASK;

        if (!(ctx.hflags & MIPS_HFLAG_M16)) {

            ctx.opcode = cpu_ldl_code(env, ctx.pc);

            insn_bytes = 4;

            decode_opc(env, &ctx);

        } else if (ctx.insn_flags & ASE_MICROMIPS) {

            ctx.opcode = cpu_lduw_code(env, ctx.pc);

            insn_bytes = decode_micromips_opc(env, &ctx);

        } else if (ctx.insn_flags & ASE_MIPS16) {

            ctx.opcode = cpu_lduw_code(env, ctx.pc);

            insn_bytes = decode_mips16_opc(env, &ctx);

        } else {

            generate_exception(&ctx, EXCP_RI);

            ctx.bstate = BS_STOP;

            break;

        }



        if (ctx.hflags & MIPS_HFLAG_BMASK) {

            if (!(ctx.hflags & (MIPS_HFLAG_BDS16 | MIPS_HFLAG_BDS32 |

                                MIPS_HFLAG_FBNSLOT))) {

                /* force to generate branch as there is neither delay nor

                   forbidden slot */

                is_slot = 1;

            }

        }

        if (is_slot) {

            gen_branch(&ctx, insn_bytes);

        }

        ctx.pc += insn_bytes;



        num_insns++;



        /* Execute a branch and its delay slot as a single instruction.

           This is what GDB expects and is consistent with what the

           hardware does (e.g. if a delay slot instruction faults, the

           reported PC is the PC of the branch).  */

        if (cs->singlestep_enabled && (ctx.hflags & MIPS_HFLAG_BMASK) == 0) {

            break;

        }



        if ((ctx.pc & (TARGET_PAGE_SIZE - 1)) == 0)

            break;



        if (tcg_ctx.gen_opc_ptr >= gen_opc_end) {

            break;

        }



        if (num_insns >= max_insns)

            break;



        if (singlestep)

            break;

    }

    if (tb->cflags & CF_LAST_IO) {

        gen_io_end();

    }

    if (cs->singlestep_enabled && ctx.bstate != BS_BRANCH) {

        save_cpu_state(&ctx, ctx.bstate == BS_NONE);

        gen_helper_0e0i(raise_exception, EXCP_DEBUG);

    } else {

        switch (ctx.bstate) {

        case BS_STOP:

            gen_goto_tb(&ctx, 0, ctx.pc);

            break;

        case BS_NONE:

            save_cpu_state(&ctx, 0);

            gen_goto_tb(&ctx, 0, ctx.pc);

            break;

        case BS_EXCP:

            tcg_gen_exit_tb(0);

            break;

        case BS_BRANCH:

        default:

            break;

        }

    }

done_generating:

    gen_tb_end(tb, num_insns);

    *tcg_ctx.gen_opc_ptr = INDEX_op_end;

    if (search_pc) {

        j = tcg_ctx.gen_opc_ptr - tcg_ctx.gen_opc_buf;

        lj++;

        while (lj <= j)

            tcg_ctx.gen_opc_instr_start[lj++] = 0;

    } else {

        tb->size = ctx.pc - pc_start;

        tb->icount = num_insns;

    }

#ifdef DEBUG_DISAS

    LOG_DISAS("\n");

    if (qemu_loglevel_mask(CPU_LOG_TB_IN_ASM)) {

        qemu_log("IN: %s\n", lookup_symbol(pc_start));

        log_target_disas(env, pc_start, ctx.pc - pc_start, 0);

        qemu_log("\n");

    }

#endif

}

```

## H2R-087

### Query

```c

static void parse_type_bool(Visitor *v, const char *name, bool *obj,

                            Error **errp)

{

    StringInputVisitor *siv = to_siv(v);



    if (siv->string) {

        if (!strcasecmp(siv->string, "on") ||

            !strcasecmp(siv->string, "yes") ||

            !strcasecmp(siv->string, "true")) {

            *obj = true;

            return;

        }

        if (!strcasecmp(siv->string, "off") ||

            !strcasecmp(siv->string, "no") ||

            !strcasecmp(siv->string, "false")) {

            *obj = false;

            return;

        }

    }



    error_setg(errp, QERR_INVALID_PARAMETER_TYPE, name ? name : "null",

               "boolean");

}

```

### Demonstration

```c

void visit_type_int8(Visitor *v, int8_t *obj, const char *name, Error **errp)

{

    int64_t value;

    if (!error_is_set(errp)) {

        if (v->type_int8) {

            v->type_int8(v, obj, name, errp);

        } else {

            value = *obj;

            v->type_int(v, &value, name, errp);

            if (value < INT8_MIN || value > INT8_MAX) {

                error_set(errp, QERR_INVALID_PARAMETER_VALUE, name ? name : "null",

                          "int8_t");

                return;

            }

            *obj = value;

        }

    }

}

```

## H2R-088

### Query

```c

static void gen_cp0 (CPUState *env, DisasContext *ctx, uint32_t opc, int rt, int rd)

{

    const char *opn = "ldst";



    switch (opc) {

    case OPC_MFC0:

        if (rt == 0) {

            /* Treat as NOP */

            return;

        }

        gen_mfc0(ctx, rd, ctx->opcode & 0x7);

        gen_op_store_T0_gpr(rt);

        opn = "mfc0";

        break;

    case OPC_MTC0:

        GEN_LOAD_REG_TN(T0, rt);

        gen_mtc0(ctx, rd, ctx->opcode & 0x7);

        opn = "mtc0";

        break;

#ifdef TARGET_MIPS64

    case OPC_DMFC0:

        if (rt == 0) {

            /* Treat as NOP */

            return;

        }

        gen_dmfc0(ctx, rd, ctx->opcode & 0x7);

        gen_op_store_T0_gpr(rt);

        opn = "dmfc0";

        break;

    case OPC_DMTC0:

        GEN_LOAD_REG_TN(T0, rt);

        gen_dmtc0(ctx, rd, ctx->opcode & 0x7);

        opn = "dmtc0";

        break;

#endif

    case OPC_TLBWI:

        opn = "tlbwi";

        if (!env->do_tlbwi)

            goto die;

        gen_op_tlbwi();

        break;

    case OPC_TLBWR:

        opn = "tlbwr";

        if (!env->do_tlbwr)

            goto die;

        gen_op_tlbwr();

        break;

    case OPC_TLBP:

        opn = "tlbp";

        if (!env->do_tlbp)

            goto die;

        gen_op_tlbp();

        break;

    case OPC_TLBR:

        opn = "tlbr";

        if (!env->do_tlbr)

            goto die;

        gen_op_tlbr();

        break;

    case OPC_ERET:

        opn = "eret";

        save_cpu_state(ctx, 0);

        gen_op_eret();

        ctx->bstate = BS_EXCP;

        break;

    case OPC_DERET:

        opn = "deret";

        if (!(ctx->hflags & MIPS_HFLAG_DM)) {

            MIPS_INVAL(opn);

            generate_exception(ctx, EXCP_RI);

        } else {

            save_cpu_state(ctx, 0);

            gen_op_deret();

            ctx->bstate = BS_EXCP;

        }

        break;

    case OPC_WAIT:

        opn = "wait";

        /* If we get an exception, we want to restart at next instruction */

        ctx->pc += 4;

        save_cpu_state(ctx, 1);

        ctx->pc -= 4;

        gen_op_wait();

        ctx->bstate = BS_EXCP;

        break;

    default:

 die:

        MIPS_INVAL(opn);

        generate_exception(ctx, EXCP_RI);

        return;

    }

    MIPS_DEBUG("%s %s %d", opn, regnames[rt], rd);

}

```

### Demonstration

```c

static void gen_cp0 (CPUMIPSState *env, DisasContext *ctx, uint32_t opc, int rt, int rd)

{

    const char *opn = "ldst";




    switch (opc) {

    case OPC_MFC0:

        if (rt == 0) {

            /* Treat as NOP. */

            return;

        }

        gen_mfc0(env, ctx, cpu_gpr[rt], rd, ctx->opcode & 0x7);

        opn = "mfc0";

        break;

    case OPC_MTC0:

        {

            TCGv t0 = tcg_temp_new();



            gen_load_gpr(t0, rt);

            gen_mtc0(env, ctx, t0, rd, ctx->opcode & 0x7);

            tcg_temp_free(t0);

        }

        opn = "mtc0";

        break;

#if defined(TARGET_MIPS64)

    case OPC_DMFC0:

        check_insn(env, ctx, ISA_MIPS3);

        if (rt == 0) {

            /* Treat as NOP. */

            return;

        }

        gen_dmfc0(env, ctx, cpu_gpr[rt], rd, ctx->opcode & 0x7);

        opn = "dmfc0";

        break;

    case OPC_DMTC0:

        check_insn(env, ctx, ISA_MIPS3);

        {

            TCGv t0 = tcg_temp_new();



            gen_load_gpr(t0, rt);

            gen_dmtc0(env, ctx, t0, rd, ctx->opcode & 0x7);

            tcg_temp_free(t0);

        }

        opn = "dmtc0";

        break;

#endif

    case OPC_MFTR:

        check_insn(env, ctx, ASE_MT);

        if (rd == 0) {

            /* Treat as NOP. */

            return;

        }

        gen_mftr(env, ctx, rt, rd, (ctx->opcode >> 5) & 1,

                 ctx->opcode & 0x7, (ctx->opcode >> 4) & 1);

        opn = "mftr";

        break;

    case OPC_MTTR:

        check_insn(env, ctx, ASE_MT);

        gen_mttr(env, ctx, rd, rt, (ctx->opcode >> 5) & 1,

                 ctx->opcode & 0x7, (ctx->opcode >> 4) & 1);

        opn = "mttr";

        break;

    case OPC_TLBWI:

        opn = "tlbwi";

        if (!env->tlb->helper_tlbwi)

            goto die;

        gen_helper_tlbwi();

        break;

    case OPC_TLBWR:

        opn = "tlbwr";

        if (!env->tlb->helper_tlbwr)

            goto die;

        gen_helper_tlbwr();

        break;

    case OPC_TLBP:

        opn = "tlbp";

        if (!env->tlb->helper_tlbp)

            goto die;

        gen_helper_tlbp();

        break;

    case OPC_TLBR:

        opn = "tlbr";

        if (!env->tlb->helper_tlbr)

            goto die;

        gen_helper_tlbr();

        break;

    case OPC_ERET:

        opn = "eret";

        check_insn(env, ctx, ISA_MIPS2);

        gen_helper_eret();

        ctx->bstate = BS_EXCP;

        break;

    case OPC_DERET:

        opn = "deret";

        check_insn(env, ctx, ISA_MIPS32);

        if (!(ctx->hflags & MIPS_HFLAG_DM)) {

            MIPS_INVAL(opn);

            generate_exception(ctx, EXCP_RI);

        } else {

            gen_helper_deret();

            ctx->bstate = BS_EXCP;

        }

        break;

    case OPC_WAIT:

        opn = "wait";

        check_insn(env, ctx, ISA_MIPS3 | ISA_MIPS32);

        /* If we get an exception, we want to restart at next instruction */

        ctx->pc += 4;

        save_cpu_state(ctx, 1);

        ctx->pc -= 4;

        gen_helper_wait();

        ctx->bstate = BS_EXCP;

        break;

    default:

 die:

        MIPS_INVAL(opn);

        generate_exception(ctx, EXCP_RI);

        return;

    }

    (void)opn; /* avoid a compiler warning */

    MIPS_DEBUG("%s %s %d", opn, regnames[rt], rd);

}

```

## H2R-089

### Query

```c

static uint64_t qdev_get_prop_mask64(Property *prop)

{

    assert(prop->info == &qdev_prop_bit);

    return 0x1 << prop->bitnr;

}

```

### Demonstration

```c

static uint64_t pmsav5_data_ap_read(CPUARMState *env, const ARMCPRegInfo *ri)

{

    return simple_mpu_ap_bits(env->cp15.c5_data);

}

```

## H2R-090

### Query

```c

static void gen_rfci(DisasContext *ctx)

{

#if defined(CONFIG_USER_ONLY)

    gen_inval_exception(ctx, POWERPC_EXCP_PRIV_OPC);

#else

    if (unlikely(ctx->pr)) {

        gen_inval_exception(ctx, POWERPC_EXCP_PRIV_OPC);

        return;

    }

    /* Restore CPU state */

    gen_helper_rfci(cpu_env);

    gen_sync_exception(ctx);

#endif

}

```

### Demonstration

```c

static void gen_rfdi(DisasContext *ctx)

{

#if defined(CONFIG_USER_ONLY)

    gen_inval_exception(ctx, POWERPC_EXCP_PRIV_OPC);

#else

    if (unlikely(ctx->pr)) {

        gen_inval_exception(ctx, POWERPC_EXCP_PRIV_OPC);

        return;

    }

    /* Restore CPU state */

    gen_helper_rfdi(cpu_env);

    gen_sync_exception(ctx);

#endif

}

```

## H2R-091

### Query

```c

static void filter_mirror_setup(NetFilterState *nf, Error **errp)
{
    MirrorState *s = FILTER_MIRROR(nf);
    Chardev *chr;
    chr = qemu_chr_find(s->outdev);
    if (chr == NULL) {
        error_set(errp, ERROR_CLASS_DEVICE_NOT_FOUND,
                  "Device '%s' not found", s->outdev);
    qemu_chr_fe_init(&s->chr_out, chr, errp);

```

### Demonstration

```c

static void filter_mirror_setup(NetFilterState *nf, Error **errp)

{

    MirrorState *s = FILTER_MIRROR(nf);



    if (!s->outdev) {

        error_setg(errp, "filter filter mirror needs 'outdev' "

                   "property set");

        return;

    }



    s->chr_out = qemu_chr_find(s->outdev);

    if (s->chr_out == NULL) {

        error_set(errp, ERROR_CLASS_DEVICE_NOT_FOUND,

                  "Device '%s' not found", s->outdev);

        return;

    }



    if (qemu_chr_fe_claim(s->chr_out) != 0) {

        error_setg(errp, QERR_DEVICE_IN_USE, s->outdev);

        return;

    }

}

```

## H2R-092

### Query

```c

static void RENAME(yuv2bgr24_1)(SwsContext *c, const int16_t *buf0,

                                const int16_t *ubuf[2], const int16_t *bguf[2],

                                const int16_t *abuf0, uint8_t *dest,

                                int dstW, int uvalpha, int y)

{

    const int16_t *ubuf0 = ubuf[0], *ubuf1 = ubuf[1];

    const int16_t *buf1= buf0; //FIXME needed for RGB1/BGR1



    if (uvalpha < 2048) { // note this is not correct (shifts chrominance by 0.5 pixels) but it is a bit faster

        __asm__ volatile(

            "mov %%"REG_b", "ESP_OFFSET"(%5)        \n\t"

            "mov        %4, %%"REG_b"               \n\t"

            "push %%"REG_BP"                        \n\t"

            YSCALEYUV2RGB1(%%REGBP, %5)

            "pxor    %%mm7, %%mm7                   \n\t"

            WRITEBGR24(%%REGb, 8280(%5), %%REGBP)

            "pop %%"REG_BP"                         \n\t"

            "mov "ESP_OFFSET"(%5), %%"REG_b"        \n\t"

            :: "c" (buf0), "d" (buf1), "S" (ubuf0), "D" (ubuf1), "m" (dest),

               "a" (&c->redDither)

        );

    } else {

        __asm__ volatile(

            "mov %%"REG_b", "ESP_OFFSET"(%5)        \n\t"

            "mov        %4, %%"REG_b"               \n\t"

            "push %%"REG_BP"                        \n\t"

            YSCALEYUV2RGB1b(%%REGBP, %5)

            "pxor    %%mm7, %%mm7                   \n\t"

            WRITEBGR24(%%REGb, 8280(%5), %%REGBP)

            "pop %%"REG_BP"                         \n\t"

            "mov "ESP_OFFSET"(%5), %%"REG_b"        \n\t"

            :: "c" (buf0), "d" (buf1), "S" (ubuf0), "D" (ubuf1), "m" (dest),

               "a" (&c->redDither)

        );

    }

}

```

### Demonstration

```c

static void RENAME(yuv2yuyv422_1)(SwsContext *c, const int16_t *buf0,

                                  const int16_t *ubuf[2], const int16_t *bguf[2],

                                  const int16_t *abuf0, uint8_t *dest,

                                  int dstW, int uvalpha, int y)

{

    const int16_t *ubuf0 = ubuf[0], *ubuf1 = ubuf[1];

    const int16_t *buf1= buf0; //FIXME needed for RGB1/BGR1



    if (uvalpha < 2048) { // note this is not correct (shifts chrominance by 0.5 pixels) but it is a bit faster

        __asm__ volatile(

            "mov %%"REG_b", "ESP_OFFSET"(%5)        \n\t"

            "mov        %4, %%"REG_b"               \n\t"

            "push %%"REG_BP"                        \n\t"

            YSCALEYUV2PACKED1(%%REGBP, %5)

            WRITEYUY2(%%REGb, 8280(%5), %%REGBP)

            "pop %%"REG_BP"                         \n\t"

            "mov "ESP_OFFSET"(%5), %%"REG_b"        \n\t"

            :: "c" (buf0), "d" (buf1), "S" (ubuf0), "D" (ubuf1), "m" (dest),

               "a" (&c->redDither)

        );

    } else {

        __asm__ volatile(

            "mov %%"REG_b", "ESP_OFFSET"(%5)        \n\t"

            "mov        %4, %%"REG_b"               \n\t"

            "push %%"REG_BP"                        \n\t"

            YSCALEYUV2PACKED1b(%%REGBP, %5)

            WRITEYUY2(%%REGb, 8280(%5), %%REGBP)

            "pop %%"REG_BP"                         \n\t"

            "mov "ESP_OFFSET"(%5), %%"REG_b"        \n\t"

            :: "c" (buf0), "d" (buf1), "S" (ubuf0), "D" (ubuf1), "m" (dest),

               "a" (&c->redDither)

        );

    }

}

```

## H2R-093

### Query

```c

static void timerlist_rearm(QEMUTimerList *timer_list)

{

    /* Interrupt execution to force deadline recalculation.  */

    if (timer_list->clock->type == QEMU_CLOCK_VIRTUAL) {

        qemu_start_warp_timer();

    }

    timerlist_notify(timer_list);

}

```

### Demonstration

```c

void timerlist_notify(QEMUTimerList *timer_list)

{

    if (timer_list->notify_cb) {

        timer_list->notify_cb(timer_list->notify_opaque);

    } else {

        qemu_notify_event();

    }

}

```

## H2R-094

### Query

```c

CharDriverState *text_console_init(DisplayState *ds, const char *p)

{

    CharDriverState *chr;

    TextConsole *s;

    unsigned width;

    unsigned height;

    static int color_inited;



    chr = qemu_mallocz(sizeof(CharDriverState));

    if (!chr)

        return NULL;

    s = new_console(ds, TEXT_CONSOLE);

    if (!s) {

        free(chr);

        return NULL;

    }

    if (!p)

        p = DEFAULT_MONITOR_SIZE;



    chr->opaque = s;

    chr->chr_write = console_puts;

    chr->chr_send_event = console_send_event;



    s->chr = chr;

    s->out_fifo.buf = s->out_fifo_buf;

    s->out_fifo.buf_size = sizeof(s->out_fifo_buf);

    s->kbd_timer = qemu_new_timer(rt_clock, kbd_send_chars, s);



    if (!color_inited) {

        color_inited = 1;

        console_color_init(s->ds);

    }

    s->y_displayed = 0;

    s->y_base = 0;

    s->total_height = DEFAULT_BACKSCROLL;

    s->x = 0;

    s->y = 0;

    width = s->ds->width;

    height = s->ds->height;

    if (p != 0) {

        width = strtoul(p, (char **)&p, 10);

        if (*p == 'C') {

            p++;

            width *= FONT_WIDTH;

        }

        if (*p == 'x') {

            p++;

            height = strtoul(p, (char **)&p, 10);

            if (*p == 'C') {

                p++;

                height *= FONT_HEIGHT;

            }

        }

    }

    s->g_width = width;

    s->g_height = height;



    s->hw_invalidate = text_console_invalidate;

    s->hw_text_update = text_console_update;

    s->hw = s;



    /* Set text attribute defaults */

    s->t_attrib_default.bold = 0;

    s->t_attrib_default.uline = 0;

    s->t_attrib_default.blink = 0;

    s->t_attrib_default.invers = 0;

    s->t_attrib_default.unvisible = 0;

    s->t_attrib_default.fgcol = COLOR_WHITE;

    s->t_attrib_default.bgcol = COLOR_BLACK;



    /* set current text attributes to default */

    s->t_attrib = s->t_attrib_default;

    text_console_resize(s);



    qemu_chr_reset(chr);



    return chr;

}

```

### Demonstration

```c

CharDriverState *chr_baum_init(void)

{

    BaumDriverState *baum;

    CharDriverState *chr;

    brlapi_handle_t *handle;

#ifdef CONFIG_SDL

    SDL_SysWMinfo info;

#endif

    int tty;



    baum = g_malloc0(sizeof(BaumDriverState));

    baum->chr = chr = g_malloc0(sizeof(CharDriverState));



    chr->opaque = baum;

    chr->chr_write = baum_write;

    chr->chr_accept_input = baum_accept_input;

    chr->chr_close = baum_close;



    handle = g_malloc0(brlapi_getHandleSize());

    baum->brlapi = handle;



    baum->brlapi_fd = brlapi__openConnection(handle, NULL, NULL);

    if (baum->brlapi_fd == -1) {

        brlapi_perror("baum_init: brlapi_openConnection");

        goto fail_handle;

    }



    baum->cellCount_timer = qemu_new_timer_ns(vm_clock, baum_cellCount_timer_cb, baum);



    if (brlapi__getDisplaySize(handle, &baum->x, &baum->y) == -1) {

        brlapi_perror("baum_init: brlapi_getDisplaySize");

        goto fail;

    }



#ifdef CONFIG_SDL

    memset(&info, 0, sizeof(info));

    SDL_VERSION(&info.version);

    if (SDL_GetWMInfo(&info))

        tty = info.info.x11.wmwindow;

    else

#endif

        tty = BRLAPI_TTY_DEFAULT;



    if (brlapi__enterTtyMode(handle, tty, NULL) == -1) {

        brlapi_perror("baum_init: brlapi_enterTtyMode");

        goto fail;

    }



    qemu_set_fd_handler(baum->brlapi_fd, baum_chr_read, NULL, baum);



    qemu_chr_be_generic_open(chr);



    return chr;



fail:

    qemu_free_timer(baum->cellCount_timer);

    brlapi__closeConnection(handle);

fail_handle:

    g_free(handle);

    g_free(chr);

    g_free(baum);

    return NULL;

}

```

## H2R-095

### Query

```c

void gdb_do_syscall(gdb_syscall_complete_cb cb, const char *fmt, ...)

{

    va_list va;

    char buf[256];

    char *p;

    target_ulong addr;

    uint64_t i64;

    GDBState *s;



    s = gdbserver_state;

    if (!s)

        return;

    gdb_current_syscall_cb = cb;

    s->state = RS_SYSCALL;

#ifndef CONFIG_USER_ONLY

    vm_stop(EXCP_DEBUG);

#endif

    s->state = RS_IDLE;

    va_start(va, fmt);

    p = buf;

    *(p++) = 'F';

    while (*fmt) {

        if (*fmt == '%') {

            fmt++;

            switch (*fmt++) {

            case 'x':

                addr = va_arg(va, target_ulong);

                p += snprintf(p, &buf[sizeof(buf)] - p, TARGET_FMT_lx, addr);

                break;

            case 'l':

                if (*(fmt++) != 'x')

                    goto bad_format;

                i64 = va_arg(va, uint64_t);

                p += snprintf(p, &buf[sizeof(buf)] - p, "%" PRIx64, i64);

                break;

            case 's':

                addr = va_arg(va, target_ulong);

                p += snprintf(p, &buf[sizeof(buf)] - p, TARGET_FMT_lx "/%x",

                              addr, va_arg(va, int));

                break;

            default:

            bad_format:

                fprintf(stderr, "gdbstub: Bad syscall format string '%s'\n",

                        fmt - 1);

                break;

            }

        } else {

            *(p++) = *(fmt++);

        }

    }

    *p = 0;

    va_end(va);

    put_packet(s, buf);

#ifdef CONFIG_USER_ONLY

    gdb_handlesig(s->c_cpu, 0);

#else

    cpu_interrupt(s->c_cpu, CPU_INTERRUPT_EXIT);

#endif

}

```

### Demonstration

```c

static void tcx_screen_dump(void *opaque, const char *filename, bool cswitch,

                            Error **errp)

{

    TCXState *s = opaque;

    FILE *f;

    uint8_t *d, *d1, v;

    int ret, y, x;



    f = fopen(filename, "wb");

    if (!f) {

        error_setg(errp, "failed to open file '%s': %s", filename,

                   strerror(errno));

        return;

    }

    ret = fprintf(f, "P6\n%d %d\n%d\n", s->width, s->height, 255);

    if (ret < 0) {

        goto write_err;

    }

    d1 = s->vram;

    for(y = 0; y < s->height; y++) {

        d = d1;

        for(x = 0; x < s->width; x++) {

            v = *d;

            ret = fputc(s->r[v], f);

            if (ret == EOF) {

                goto write_err;

            }

            ret = fputc(s->g[v], f);

            if (ret == EOF) {

                goto write_err;

            }

            ret = fputc(s->b[v], f);

            if (ret == EOF) {

                goto write_err;

            }

            d++;

        }

        d1 += MAXX;

    }



out:

    fclose(f);

    return;



write_err:

    error_setg(errp, "failed to write to file '%s': %s", filename,

               strerror(errno));

    unlink(filename);

    goto out;

}

```

## H2R-096

### Query

```c

uint32_t lduw_be_phys(target_phys_addr_t addr)

{

    return lduw_phys_internal(addr, DEVICE_BIG_ENDIAN);

}

```

### Demonstration

```c

uint32_t lduw_le_phys(target_phys_addr_t addr)

{

    return lduw_phys_internal(addr, DEVICE_LITTLE_ENDIAN);

}

```

## H2R-097

### Query

```c

static void init_excp_BookE (CPUPPCState *env)

{

#if !defined(CONFIG_USER_ONLY)

    env->excp_vectors[POWERPC_EXCP_CRITICAL] = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_MCHECK]   = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_DSI]      = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_ISI]      = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_EXTERNAL] = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_ALIGN]    = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_PROGRAM]  = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_FPU]      = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_SYSCALL]  = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_APU]      = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_DECR]     = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_FIT]      = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_WDT]      = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_DTLB]     = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_ITLB]     = 0x00000000;

    env->excp_vectors[POWERPC_EXCP_DEBUG]    = 0x00000000;

    env->excp_prefix = 0x00000000;

    env->ivor_mask = 0x0000FFE0;

    env->ivpr_mask = 0xFFFF0000;

    /* Hardware reset vector */

    env->hreset_vector = 0xFFFFFFFCUL;

#endif

}

```

### Demonstration

```c

static void init_excp_4xx_real (CPUPPCState *env)

{

#if !defined(CONFIG_USER_ONLY)

    env->excp_vectors[POWERPC_EXCP_CRITICAL] = 0x00000100;

    env->excp_vectors[POWERPC_EXCP_MCHECK]   = 0x00000200;

    env->excp_vectors[POWERPC_EXCP_EXTERNAL] = 0x00000500;

    env->excp_vectors[POWERPC_EXCP_ALIGN]    = 0x00000600;

    env->excp_vectors[POWERPC_EXCP_PROGRAM]  = 0x00000700;

    env->excp_vectors[POWERPC_EXCP_SYSCALL]  = 0x00000C00;

    env->excp_vectors[POWERPC_EXCP_PIT]      = 0x00001000;

    env->excp_vectors[POWERPC_EXCP_FIT]      = 0x00001010;

    env->excp_vectors[POWERPC_EXCP_WDT]      = 0x00001020;

    env->excp_vectors[POWERPC_EXCP_DEBUG]    = 0x00002000;

    env->excp_prefix = 0x00000000;

    env->ivor_mask = 0x0000FFF0;

    env->ivpr_mask = 0xFFFF0000;

    /* Hardware reset vector */

    env->hreset_vector = 0xFFFFFFFCUL;

#endif

}

```

## H2R-098

### Query

```c

static inline void mct_decode(Jpeg2000DecoderContext *s, Jpeg2000Tile *tile)

{

    int i, csize = 1;

    void *src[3];



    for (i = 1; i < 3; i++)

        if (tile->codsty[0].transform != tile->codsty[i].transform) {

            av_log(s->avctx, AV_LOG_ERROR, "Transforms mismatch, MCT not supported\n");

            return;

        }



    for (i = 0; i < 3; i++)

        if (tile->codsty[0].transform == FF_DWT97)

            src[i] = tile->comp[i].f_data;

        else

            src[i] = tile->comp[i].i_data;



    for (i = 0; i < 2; i++)

        csize *= tile->comp[0].coord[i][1] - tile->comp[0].coord[i][0];



    s->dsp.mct_decode[tile->codsty[0].transform](src[0], src[1], src[2], csize);

}

```

### Demonstration

```c

static int genh_read_packet(AVFormatContext *s, AVPacket *pkt)

{

    AVCodecContext *codec = s->streams[0]->codec;

    GENHDemuxContext *c = s->priv_data;

    int ret;



    if (c->dsp_int_type == 1 && codec->codec_id == AV_CODEC_ID_ADPCM_THP &&

        codec->channels > 1) {

        int i, ch;



        if (avio_feof(s->pb))

            return AVERROR_EOF;

        av_new_packet(pkt, 8 * codec->channels);

        for (i = 0; i < 8 / c->interleave_size; i++) {

            for (ch = 0; ch < codec->channels; ch++) {

                pkt->data[ch * 8 + i*c->interleave_size+0] = avio_r8(s->pb);

                pkt->data[ch * 8 + i*c->interleave_size+1] = avio_r8(s->pb);

            }

        }

        ret = 0;

    } else {

        ret = av_get_packet(s->pb, pkt, codec->block_align ? codec->block_align : 1024 * codec->channels);

    }



    pkt->stream_index = 0;

    return ret;

}

```

## H2R-099

### Query

```c

uint64_t helper_sublv (uint64_t op1, uint64_t op2)

{

    uint64_t tmp = op1;

    op1 = (uint32_t)(op1 - op2);

    if (unlikely(((~tmp) ^ op1 ^ (-1UL)) & ((~tmp) ^ op2) & (1UL << 31))) {

        helper_excp(EXCP_ARITH, EXCP_ARITH_OVERFLOW);

    }

    return op1;

}

```

### Demonstration

```c

uint64_t helper_addlv(CPUAlphaState *env, uint64_t op1, uint64_t op2)

{

    uint64_t tmp = op1;

    op1 = (uint32_t)(op1 + op2);

    if (unlikely((tmp ^ op2 ^ (-1UL)) & (tmp ^ op1) & (1UL << 31))) {

        arith_excp(env, GETPC(), EXC_M_IOV, 0);

    }

    return op1;

}

```

## H2R-100

### Query

```c

int av_get_channel_layout_nb_channels(int64_t channel_layout)

{

    int count;

    uint64_t x = channel_layout;

    for (count = 0; x; count++)

        x &= x-1; // unset lowest set bit

    return count;

}

```

### Demonstration

```c

static int64_t truehd_layout(int chanmap)

{

    int layout = 0, i;



    for (i = 0; i < 13; i++)

        layout |= thd_layout[i] * ((chanmap >> i) & 1);



    return layout;

}

```