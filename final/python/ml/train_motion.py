import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
import os
import numpy as np

from motionnet import MotionNet
from motionset import MotionSet

config = {
    "data_dir": "../../data/filter_data_raw_80_1.csv",
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "batch_size": 4,
    "lr": 1e-5,
    "weight_decay": 5e-6,
    "epoch": 1000,
    "model_save_dir": "../../models",
    "loss_fn": torch.nn.CrossEntropyLoss()
}

def hook(module, feat_in, feat_out: torch.TensorType):
    p = feat_out.detach().cpu().numpy()
    min_value, max_value = np.min(p), np.max(p)
    # print("Min: %f, max: %f" % (min_value, max_value))
    int_bits = int(np.ceil(np.log2(max(abs(min_value), abs(max_value)))))
    dec_bits = 15 - int_bits
    # print("Int bits: %d, dec bits: %d" % (int_bits, dec_bits))



def train():
    train_set = MotionSet(config["data_dir"])
    print("Train set length: %d" % len(train_set))
    train_loader = DataLoader(train_set, batch_size=config["batch_size"], shuffle=True)

    device = config["device"]
    print("Using device: %s" % device)

    model = MotionNet()
    model.to(device)

    epoch = config["epoch"]
    optimizer = torch.optim.Adam(model.parameters(), lr=config["lr"], weight_decay=config["weight_decay"])
    loss_fn = config["loss_fn"]

    # for layer in model.mlp.children():
    #     if isinstance(layer, torch.nn.Linear):
    #         layer.register_forward_hook(hook=hook)

    best_acc = 0.0
    model.train()
    for e in range(epoch):
        # l: 0, r: 1, s: 2, n: 3
        correct = [0, 0, 0, 0]
        in_correct = [0, 0, 0, 0]

        train_loss, train_acc = [], []
        for batch in tqdm(train_loader):
            motion, label = batch
            motion, label = motion.to(device), label.to(device)

            output = model(motion)
            
            loss = loss_fn(output, label)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            pred = output.argmax(dim=-1)
            for i, p in enumerate(pred):
                if p == label[i]:
                    correct[label[i]] += 1
                else:
                    in_correct[label[i]] += 1

            acc = (pred == label).float().mean()
            train_loss.append(loss.item())
            train_acc.append(acc.item())

        train_loss = sum(train_loss) / len(train_loss)
        train_acc = sum(train_acc) / len(train_acc)
        if best_acc < train_acc:
            best_acc = train_acc
            print(best_acc)
            if best_acc > 0.85:
                save_path = os.path.join(config["model_save_dir"], "motion_%d.ckpt" % int(best_acc * 100))
                print("Saving model at %s" % save_path)
                torch.save(model.state_dict(), save_path)
        
        print(f"[Overall {e + 1:04d}/{epoch:04d}] train loss: {train_loss:.5f}, train acc: {train_acc:.5f}, best train acc:{best_acc:.5f}")
        print("Confution matrix:")
        print("Left correct: %d, left incorrect: %d" % (correct[0], in_correct[0]))
        print("Right correct: %d, right incorrect: %d" % (correct[1], in_correct[1]))
        print("Stop correct: %d, stop incorrect: %d" % (correct[2], in_correct[2]))
        print("None correct: %d, none incorrect: %d" % (correct[3], in_correct[3]))

if __name__ == "__main__":
    train()