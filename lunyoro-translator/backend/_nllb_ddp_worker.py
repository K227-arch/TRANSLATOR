
import os, sys
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import torch, torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import Dataset, DataLoader, DistributedSampler
from torch.optim import AdamW
from transformers import NllbTokenizer, AutoModelForSeq2SeqLM, get_cosine_schedule_with_warmup
import pandas as pd
from pathlib import Path

EPOCHS = 8; PER_GPU = 8; ACCUM = 4; LR = 2e-05; LS = 0.2
DATA_DIR  = Path(r"C:\Users\MarvinCliveTwesige\OneDrive\Desktop\PROJECTS\TRANSLATOR\lunyoro-translator\backend\data\training")
MODEL_DIR = Path(r"C:\Users\MarvinCliveTwesige\OneDrive\Desktop\PROJECTS\TRANSLATOR\lunyoro-translator\backend\model")
LANG_EN   = "eng_Latn"

dist.init_process_group("gloo")   # gloo works on Windows; nccl requires Linux
rank       = dist.get_rank()
world_size = dist.get_world_size()
device     = torch.device(f"cuda:{rank}")
torch.cuda.set_device(device)

class NLLBDataset(Dataset):
    def __init__(self, df, tok, sc, tc, sl, tl, max_len=128):
        self.tok=tok; self.src=df[sc].tolist(); self.tgt=df[tc].tolist()
        self.sl=sl; self.tl=tl; self.max_len=max_len
    def __len__(self): return len(self.src)
    def __getitem__(self, idx):
        self.tok.src_lang=self.sl
        s=self.tok(self.src[idx],max_length=self.max_len,truncation=True,padding="max_length",return_tensors="pt")
        self.tok.src_lang=self.tl
        t=self.tok(self.tgt[idx],max_length=self.max_len,truncation=True,padding="max_length",return_tensors="pt")
        lbl=t["input_ids"].squeeze(); lbl[lbl==self.tok.pad_token_id]=-100
        return {"input_ids":s["input_ids"].squeeze(),"attention_mask":s["attention_mask"].squeeze(),"labels":lbl}

train_df = pd.read_csv(DATA_DIR/"train.csv").fillna("")
val_df   = pd.read_csv(DATA_DIR/"val.csv").fillna("")

for direction, sc, tc, sl, tl in [
    ("nllb_en2lun","english","lunyoro",LANG_EN,LANG_EN),
    ("nllb_lun2en","lunyoro","english",LANG_EN,LANG_EN),
]:
    ckpt = str(MODEL_DIR/direction)
    tok  = NllbTokenizer.from_pretrained(ckpt)
    mdl  = AutoModelForSeq2SeqLM.from_pretrained(ckpt)
    mdl.config.label_smoothing_factor = LS
    mdl.gradient_checkpointing_enable()
    mdl = mdl.to(device)
    mdl = DDP(mdl, device_ids=[rank], find_unused_parameters=False)

    train_ds = NLLBDataset(train_df,tok,sc,tc,sl,tl)
    val_ds   = NLLBDataset(val_df,tok,sc,tc,sl,tl)
    train_sampler = DistributedSampler(train_ds, num_replicas=world_size, rank=rank, shuffle=True)
    train_loader  = DataLoader(train_ds, batch_size=PER_GPU, sampler=train_sampler, num_workers=0, pin_memory=True)
    val_loader    = DataLoader(val_ds,   batch_size=PER_GPU, shuffle=False, num_workers=0, pin_memory=True)

    optimizer = AdamW(mdl.module.parameters(), lr=LR, weight_decay=0.01)
    total_steps = (len(train_loader)//ACCUM)*EPOCHS
    scheduler = get_cosine_schedule_with_warmup(optimizer, total_steps//10, total_steps)

    best_val = float("inf")
    for epoch in range(1, EPOCHS+1):
        train_sampler.set_epoch(epoch)
        mdl.train(); t_loss=0.0; optimizer.zero_grad()
        for step, batch in enumerate(train_loader):
            batch={k:v.to(device) for k,v in batch.items()}
            loss=mdl(**batch).loss
            if loss.dim()>0: loss=loss.mean()
            (loss/ACCUM).backward(); t_loss+=loss.item()
            if (step+1)%ACCUM==0:
                torch.nn.utils.clip_grad_norm_(mdl.parameters(),1.0)
                optimizer.step(); scheduler.step(); optimizer.zero_grad()
        torch.nn.utils.clip_grad_norm_(mdl.parameters(),1.0)
        optimizer.step(); optimizer.zero_grad()
        t_loss/=len(train_loader)
        if rank==0:
            mdl.eval(); v_loss=0.0
            with torch.no_grad():
                for batch in val_loader:
                    batch={k:v.to(device) for k,v in batch.items()}
                    v_loss+=mdl(**batch).loss.mean().item()
            v_loss/=len(val_loader)
            print(f"  [{direction}] Epoch {epoch}/{EPOCHS}  train={t_loss:.4f}  val={v_loss:.4f}", flush=True)
            if v_loss<best_val:
                best_val=v_loss
                mdl.module.save_pretrained(ckpt); tok.save_pretrained(ckpt)
                print(f"  OK Saved (val={v_loss:.4f})", flush=True)
    if rank==0:
        print(f"  Done. Best val_loss={best_val:.4f}", flush=True)
    torch.cuda.empty_cache()

dist.destroy_process_group()
