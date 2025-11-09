import io, pandas as pd


def preview_table(file_bytes: bytes, filename: str):
    buf = io.BytesIO(file_bytes)
    if filename.endswith(".csv"):
        df = pd.read_csv(buf)
    else:
        df = pd.read_excel(buf)
    return df.head(5).to_dict(orient="records"), list(df.columns)


def bar_png(df, x_col, y_col):
    import matplotlib.pyplot as plt
    import base64
    fig, ax = plt.subplots()
    df.groupby(x_col)[y_col].sum().plot(kind="bar", ax=ax)
    out = io.BytesIO()
    plt.tight_layout(); fig.savefig(out, format="png"); plt.close(fig)
    out.seek(0)
    return out.read()