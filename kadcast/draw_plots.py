import pandas as pd
import numpy as np
import matplotlib.pyplot as plt



df = pd.read_csv("csv/firstspy_mul.csv")
#df = df[["TXS", "NODES", "FRAC_SPIES", "PRECISION", "RECALL", "KAD_K", "ID_LEN"]]
df = df[["TXS", "NODES", "FRAC_SPIES", "PRECISION", "RECALL"]]


for n in df["NODES"].unique():
    df_n = df[df["NODES"] == n]
    for txs in df["TXS"].unique():
        fig, ax = plt.subplots()
        #ax.plot(x, y)
        #ax.set_title('A single plot')

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
        #y1 = df_n_tx["PRECISION"]
        #x1 = df_n_tx["FRAC_SPIES"]
        #ax.plot(x1, y1, label="Precision")
        ax.errorbar(x1+0.007, y1, yerr=p_std_dev, fmt='o', label="Precision")
        #print(p_means)


        y2 = r_means
        x2 = df_n_tx["FRAC_SPIES"].unique()
        #print(r_means)
        #print(r_std_dev)
        #y2 = df_n_tx["RECALL"]
        #x2 = df_n_tx["FRAC_SPIES"]
        # plotting the line 2 points
        #ax.plot(x2, y2, label="Recall")
        ax.errorbar(x2-0.007, y2, yerr=r_std_dev, fmt='o', label="Recall")

        # naming the y axis
        plt.ylabel('Precision/Recall')
        # naming the x axis
        plt.xlabel('Fraction of spies')
        # giving a title to my graph
        #plt.title("PRECISION/RECALL - 200 NODES, %d TXs" % txs)
        ax.set_title("PRECISION/RECALL - %d NODES, %d TXs" % (n, txs))

        # show a legend on the plot
        plt.legend()

        # function to show the plot
        #plt.show()
        plt.savefig("plots/plot_%d_%d.png" % (n, txs))
        fig.clf()
        #plt.cla(ax)
