from flask import Flask, request, jsonify, send_from_directory, session, redirect
import sqlite3
import json

app = Flask(__name__)
app.secret_key = "berber-gizli-anahtar-2026"


def db():
    conn = sqlite3.connect("randevular.db")
    conn.row_factory = sqlite3.Row
    return conn


def ayarlari_oku():
    with open("ayarlar.json", "r", encoding="utf-8") as dosya:
        return json.load(dosya)


def tablo_olustur():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS randevular (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL,
            telefon TEXT NOT NULL,
            berber TEXT,
            hizmet TEXT,
            tarih TEXT NOT NULL,
            saat TEXT NOT NULL
        )
    """)

    sutunlar = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(randevular)").fetchall()
    ]

    if "berber" not in sutunlar:
        conn.execute(
            "ALTER TABLE randevular ADD COLUMN berber TEXT"
        )

    if "hizmet" not in sutunlar:
        conn.execute(
            "ALTER TABLE randevular ADD COLUMN hizmet TEXT"
        )

    conn.commit()
    conn.close()


tablo_olustur()


@app.route("/")
def ana_sayfa():
    return send_from_directory(".", "berber_randevu_index.html")


@app.route("/api/ayarlar", methods=["GET"])
def ayarlar():
    try:
        return jsonify(ayarlari_oku())
    except Exception as hata:
        return jsonify({
            "hata": "Ayarlar okunamadı",
            "detay": str(hata)
        }), 500


@app.route("/giris", methods=["GET", "POST"])
def giris():

    if request.method == "POST":

        kullanici = request.form.get("kullanici")
        sifre = request.form.get("sifre")

        if kullanici == "admin" and sifre == "1234":
            session["giris_yapildi"] = True
            return redirect("/panel")

    return send_from_directory(".", "berber_giris.html")


@app.route("/panel")
def panel():

    if not session.get("giris_yapildi"):
        return redirect("/giris")

    return send_from_directory(".", "berber_paneli.html")


@app.route("/api/randevular", methods=["GET"])
def randevular():

    if not session.get("giris_yapildi"):
        return jsonify({
            "hata": "Yetkisiz erişim"
        }), 401

    conn = db()

    kayitlar = conn.execute("""
        SELECT * FROM randevular
        ORDER BY tarih, saat
    """).fetchall()

    conn.close()

    return jsonify([
        dict(x) for x in kayitlar
    ])


@app.route("/api/dolu-saatler", methods=["GET"])
def dolu_saatler():

    berber = request.args.get("berber")
    tarih = request.args.get("tarih")

    if not berber or not tarih:
        return jsonify([])

    conn = db()

    kayitlar = conn.execute("""
        SELECT saat
        FROM randevular
        WHERE berber = ? AND tarih = ?
    """, (berber, tarih)).fetchall()

    conn.close()

    return jsonify([
        row["saat"] for row in kayitlar
    ])


@app.route("/api/randevu", methods=["POST"])
def randevu_ekle():

    veri = request.get_json()

    if not veri:
        return jsonify({
            "hata": "Bilgiler alınamadı"
        }), 400

    ad = veri.get("ad") or veri.get("name")
    telefon = veri.get("telefon") or veri.get("phone")
    berber = veri.get("berber") or veri.get("barber")
    hizmet = veri.get("hizmet") or veri.get("service")
    tarih = veri.get("tarih")
    saat = veri.get("saat")

    if not all([
        ad,
        telefon,
        berber,
        hizmet,
        tarih,
        saat
    ]):
        return jsonify({
            "hata": "Tüm alanları doldurun"
        }), 400

    conn = db()

    mevcut = conn.execute("""
        SELECT id
        FROM randevular
        WHERE berber = ?
        AND tarih = ?
        AND saat = ?
    """, (berber, tarih, saat)).fetchone()

    if mevcut:
        conn.close()

        return jsonify({
            "hata": "Bu berber bu tarih ve saatte dolu"
        }), 409

    conn.execute("""
        INSERT INTO randevular
        (ad, telefon, berber, hizmet, tarih, saat)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        ad,
        telefon,
        berber,
        hizmet,
        tarih,
        saat
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "mesaj": "Randevu başarıyla oluşturuldu"
    })


@app.route(
    "/api/randevu/<int:randevu_id>",
    methods=["DELETE"]
)
def randevu_sil(randevu_id):

    if not session.get("giris_yapildi"):
        return jsonify({
            "hata": "Yetkisiz erişim"
        }), 401

    conn = db()

    kayit = conn.execute(
        "SELECT id FROM randevular WHERE id = ?",
        (randevu_id,)
    ).fetchone()

    if not kayit:
        conn.close()

        return jsonify({
            "hata": "Randevu bulunamadı"
        }), 404

    conn.execute(
        "DELETE FROM randevular WHERE id = ?",
        (randevu_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "mesaj": "Randevu silindi"
    })


@app.route("/cikis")
def cikis():
    session.clear()
    return redirect("/giris")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )