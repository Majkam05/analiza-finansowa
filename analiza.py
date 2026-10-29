"""Porównanie rentowności i efektywności czterech największych banków z GPW (2023–2025).

Uruchomienie:
    pip install -r requirements.txt
    python analiza.py

Skrypt wczytuje dane z data/banki_gpw.csv, liczy dodatkowe wskaźniki,
wypisuje tabelę podsumowującą i zapisuje wykresy do folderu wykresy/.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # zapis do plików bez okna graficznego
import matplotlib.pyplot as plt
import pandas as pd

KATALOG = Path(__file__).parent
PLIK_DANYCH = KATALOG / "data" / "banki_gpw.csv"
KATALOG_WYKRESOW = KATALOG / "wykresy"

KOLORY = {
    "PKO BP": "#1f4e79",
    "Pekao": "#c0392b",
    "mBank": "#e67e22",
    "Santander BP": "#7f8c8d",
}


def wczytaj_dane(sciezka: Path = PLIK_DANYCH) -> pd.DataFrame:
    """Wczytuje dane i dolicza wskaźniki pochodne."""
    df = pd.read_csv(sciezka)
    df = df.sort_values(["bank", "rok"]).reset_index(drop=True)

    # ROA liczone na aktywach z końca roku (uproszczenie: banki raportują
    # ROA na średnich aktywach, więc wynik może się minimalnie różnić).
    df["roa_proc"] = df["zysk_netto_mln"] / df["aktywa_mln"] * 100

    # Dynamika zysku i aktywów rok do roku.
    df["zysk_rdr_proc"] = df.groupby("bank")["zysk_netto_mln"].pct_change() * 100
    df["aktywa_rdr_proc"] = df.groupby("bank")["aktywa_mln"].pct_change() * 100
    return df


def tabela_podsumowania(df: pd.DataFrame, rok: int) -> pd.DataFrame:
    """Zestawienie banków w danym roku, posortowane wg ROE."""
    kolumny = {
        "zysk_netto_mln": "Zysk netto (mln zł)",
        "aktywa_mln": "Aktywa (mld zł)",
        "roe_proc": "ROE (%)",
        "roa_proc": "ROA (%)",
        "ci_proc": "C/I (%)",
        "zysk_rdr_proc": "Zysk r/r (%)",
    }
    t = df[df["rok"] == rok].set_index("bank")[list(kolumny)].copy()
    t["aktywa_mln"] = t["aktywa_mln"] / 1000
    t = t.rename(columns=kolumny).sort_values("ROE (%)", ascending=False)
    return t.round(1)


def _zapisz(fig: plt.Figure, nazwa: str) -> Path:
    KATALOG_WYKRESOW.mkdir(exist_ok=True)
    sciezka = KATALOG_WYKRESOW / nazwa
    fig.tight_layout()
    fig.savefig(sciezka, dpi=150)
    plt.close(fig)
    return sciezka


def _styl(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)


def wykres_zysk_netto(df: pd.DataFrame) -> Path:
    tabela = df.pivot(index="rok", columns="bank", values="zysk_netto_mln") / 1000
    tabela = tabela[list(KOLORY)]
    fig, ax = plt.subplots(figsize=(9, 5))
    tabela.plot(kind="bar", ax=ax, color=[KOLORY[b] for b in tabela.columns], width=0.8)
    ax.set_title("Zysk netto przypisany akcjonariuszom", loc="left", fontweight="bold")
    ax.set_ylabel("mld zł")
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(frameon=False, ncol=4, loc="upper left")
    _styl(ax)
    return _zapisz(fig, "1_zysk_netto.png")


def wykres_linia(df: pd.DataFrame, kolumna: str, tytul: str, nazwa: str, opis_osi: str) -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    for bank, dane in df.groupby("bank"):
        ax.plot(dane["rok"], dane[kolumna], marker="o", linewidth=2.5,
                color=KOLORY[bank], label=bank)

    # Etykiety wartości z ostatniego roku, rozsunięte, żeby się nie nakładały.
    ostatni_rok = df["rok"].max()
    ostatnie = df[df["rok"] == ostatni_rok].sort_values(kolumna)
    zakres = df[kolumna].max() - df[kolumna].min()
    odstep = zakres * 0.06
    pozycje: list[float] = []
    for wartosc in ostatnie[kolumna]:
        y = wartosc if not pozycje else max(wartosc, pozycje[-1] + odstep)
        pozycje.append(y)
    for (_, w), y in zip(ostatnie.iterrows(), pozycje):
        ax.annotate(f"{w[kolumna]:.1f}", xy=(ostatni_rok, w[kolumna]),
                    xytext=(ostatni_rok + 0.06, y), va="center",
                    color=KOLORY[w["bank"]], fontweight="bold", annotation_clip=False)
    ax.set_title(tytul, loc="left", fontweight="bold")
    ax.set_ylabel(opis_osi)
    ax.set_xticks(sorted(df["rok"].unique()))
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    _styl(ax)
    return _zapisz(fig, nazwa)


def wykres_roe_vs_ci(df: pd.DataFrame, rok: int) -> Path:
    d = df[df["rok"] == rok]
    fig, ax = plt.subplots(figsize=(8, 6))
    for _, w in d.iterrows():
        rozmiar = w["aktywa_mln"] / 400
        ax.scatter(w["ci_proc"], w["roe_proc"], s=rozmiar,
                   color=KOLORY[w["bank"]], alpha=0.75, edgecolor="white", linewidth=1.5)
        # rozmiar to pole koła w pt², więc promień = sqrt(pole) / 2
        ax.annotate(w["bank"], (w["ci_proc"], w["roe_proc"]), xytext=(0, rozmiar**0.5 / 2 + 6),
                    textcoords="offset points", ha="center", fontweight="bold")
    ax.set_title(f"Rentowność a efektywność kosztowa ({rok})", loc="left", fontweight="bold")
    ax.set_xlabel("C/I (%) – im niżej, tym taniej bank zarabia")
    ax.set_ylabel("ROE (%)")
    ax.margins(0.25)
    ax.text(0.99, 0.02, "wielkość koła = suma bilansowa", transform=ax.transAxes,
            ha="right", fontsize=9, alpha=0.7)
    _styl(ax)
    return _zapisz(fig, "4_roe_vs_ci.png")


def main() -> None:
    df = wczytaj_dane()
    ostatni_rok = int(df["rok"].max())

    pd.set_option("display.width", 120)
    print(f"\nPodsumowanie za {ostatni_rok} r.\n")
    print(tabela_podsumowania(df, ostatni_rok).to_string())

    zapisane = [
        wykres_zysk_netto(df),
        wykres_linia(df, "roe_proc", "ROE – zwrot z kapitału własnego", "2_roe.png", "%"),
        wykres_linia(df, "ci_proc", "C/I – koszty w relacji do dochodów", "3_ci.png", "%"),
        wykres_roe_vs_ci(df, ostatni_rok),
    ]
    print("\nZapisane wykresy:")
    for sciezka in zapisane:
        print(f"  {sciezka.relative_to(KATALOG)}")


if __name__ == "__main__":
    main()
