import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import scipy.stats
import sys

# Create the parser
parser = argparse.ArgumentParser(description='Draw plot')

# Add the arguments
parser.add_argument('filename_in',
                       metavar='filename_in',
                       type=str,
                       help='name of csv')

parser.add_argument('filename_out',
                       metavar='filename_out',
                       type=str,
                       help='name of png')

parser.add_argument('-q', metavar='N', type=float, default=0.5, help="dandelion Q parameter")

parser.add_argument('-k', metavar='N', type=int, default=20, help="K")

parser.add_argument('--use_dand', dest='use_dand', default=False, action='store_true', help='use dandelion')

parser.add_argument('--conf', dest='conf', default=False, action='store_true', help='use confidence interval instead of standard deviation')


# Execute the parse_args() method
args = parser.parse_args()

print(args)

use_dand = args.use_dand
use_conf = args.conf
#dand_q = args.q
filename_in = args.filename_in
filename_in = "csv/"+filename_in

filename_out = args.filename_out
filename_out = "plots/"+filename_out

use_dand = args.use_dand
dand_q = args.q
k = args.k

df = pd.read_csv(filename_in)
#df = df[["TXS", "NODES", "FRAC_SPIES", "PRECISION", "RECALL", "KAD_K", "ID_LEN"]]
df = df[["TXS", "NODES", "FRAC_SPIES", "PRECISION", "RECALL"]]


for n in df["NODES"].unique():
    df_n = df[df["NODES"] == n]
    for txs in df["TXS"].unique():
        fig, ax = plt.subplots()

        df_n_tx = df_n[df_n["TXS"] == txs]
        #print(df_n_tx)

        p_means = []
        p_std_dev = []
        r_means = []
        r_std_dev = []

        for frac_spy in df_n_tx["FRAC_SPIES"].unique():
            means = np.mean(df_n_tx[df_n_tx["FRAC_SPIES"] == frac_spy])
            print(df_n_tx[df_n_tx["FRAC_SPIES"] == frac_spy])
            #print(means)
            p_means.append(means["PRECISION"])
            r_means.append(means["RECALL"])

            std = np.std(df_n_tx[df_n_tx["FRAC_SPIES"] == frac_spy])
            #print(std)
            p_std_dev.append(std["PRECISION"])
            r_std_dev.append(std["RECALL"])

        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.0])

        y1 = p_means
        x1 = df_n_tx["FRAC_SPIES"].unique()
        #print(x1)
        #print(p_means)
        #print(p_std_dev)
        ax.errorbar(x1+0.007, y1, yerr=p_std_dev, fmt='o', label="Precision")
        #print(p_means)


        y2 = r_means
        x2 = df_n_tx["FRAC_SPIES"].unique()
        #print(r_means)
        #print(r_std_dev)
        # plotting the line 2 points
        ax.errorbar(x2-0.007, y2, yerr=r_std_dev, fmt='o', label="Recall")

        # naming the y axis
        plt.ylabel('Precision/Recall')
        # naming the x axis
        plt.xlabel('Fraction of spies')
        # giving a title to my graph
        if use_dand:
            ax.set_title("Dandelion - PRECISION/RECALL | %d NODES, %d TXs | k=%d, q=%0.1f" % (n, txs, k, dand_q))
        else:
            ax.set_title("PRECISION/RECALL | %d NODES, %d TXs | k=%d" % (n, txs, k))

        # show a legend on the plot
        plt.legend()

        # save plot
        plt.savefig(filename_out)
        fig.clf()
