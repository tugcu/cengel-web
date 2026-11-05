#!/usr/bin/env python3
"""
Çengel bulmaca veritabanını üretir (zor seviye). Her kelime en fazla bir
bulmacada kullanılır; böylece hiçbir ipucu veya cevap bulmacalar arasında tekrar etmez.

Her konu için bir kelime havuzu tanımlıdır. Havuzdan rastgele kelime kümeleri
seçilir, her küme gerçek yerleştirme motoruyla (CrosswordEngine) denenir ve
yeterince kelime yerleşenler bulmaca olarak kaydedilir.

Çıktı: app/src/main/assets/puzzles.json (uygulamaya gömülür) ve
       puzzles.json (GitHub deposuna yüklenir, uzaktan güncelleme için).

Kullanım:  python3 tools/make_bank.py

Her güncellemede BANK_VERSION'ı bir alt sürüm artır (1.6 -> 1.7).
Ek kelimeler tools/wordlists/<konu>.txt dosyalarından okunur (satır: CEVAP|ipucu).
Copyright (c) 2026 Tuna Tuğcu. Tüm hakları saklıdır.
"""

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_SRC = os.path.join(ROOT, "app", "src", "main", "java", "com", "tunatugcu",
                          "cengelbulmaca", "CrosswordEngine.java")
CHECK_SRC = os.path.join(ROOT, "tests", "BankCheck.java")
ASSET_OUT = os.path.join(ROOT, "app", "src", "main", "assets", "puzzles.json")
ROOT_OUT = os.path.join(ROOT, "puzzles.json")

BANK_VERSION = "1.6"
ID_PREFIX = "tek"
WORDLIST_DIR = os.path.join(ROOT, "tools", "wordlists")
PUZZLES_PER_TOPIC = 200
SUBSET_MIN = 9
SUBSET_MAX = 11
CANDIDATES_PER_TOPIC = 1500
MIN_PLACED_PREFERRED = 8
MIN_PLACED_FALLBACK = 7

# Her konu: (anahtar, başlık, [(CEVAP, ipucu), ...])
TOPICS = [
    ("ataturk", "Atatürk ve Cumhuriyet", [
        ("MONDROS", "1918'de imzalanan ateşkes antlaşmasının adı"),
        ("SEVRES", "1920'de imzalanan ve Türk halkınca kabul edilmeyen antlaşma"),
        ("MUDANYA", "1922'de ateşkesin imzalandığı Marmara kenti"),
        ("MİLLİHAKİMİYET", "Egemenliğin millete ait olduğunu belirten ilke"),
        ("KUVAYIMİLLİYE", "Milli Mücadele'de kurulan gönüllü birlikler"),
        ("LAİKLİK", "Devletin dinden bağımsız olduğu ilke"),
        ("İNKILAP", "Köklü değişim anlamına gelen kelime"),
        ("CUMHURİYETÇİLİK", "Atatürk ilkelerinden biri: yönetimin halkın seçimine dayanması"),
        ("MİLLİYETÇİLİK", "Atatürk ilkelerinden biri: ulusal birlik ve bağımsızlık"),
        ("HALKÇILIK", "Atatürk ilkelerinden biri: toplumun eşitliğini savunan ilke"),
        ("DEVLETÇİLİK", "Ekonomide devletin rolünü öngören ilke"),
        ("ÇANKAYA", "Atatürk'ün Ankara'daki köşkünün bulunduğu semt"),
        ("TBMM", "Egemenliğin kullanıldığı kurum"),
        ("KURTULUŞ", "Mondros sonrası ulusal mücadelenin amacı"),
        ("ERZURUM", "1919'da ilk kongrenin yapıldığı doğu kenti"),
        ("SİVAS", "1919'da ikinci kongrenin yapıldığı kent"),
        ("KONGRE", "1919'da Erzurum ve Sivas'ta yapılan toplantı"),
        ("LOZAN", "1923'te imzalanan barış antlaşması"),
        ("SAKARYA", "1921'de Yunan ordusunun durdurulduğu savaş"),
        ("DUMLUPINAR", "1922'de yapılan son büyük meydan savaşı"),
        ("ALFABE", "1928'de kabul edilen yeni yazı sistemi"),
        ("GAZİ", "Atatürk'ün aldığı unvanlardan biri"),
        ("MECLİS", "Milletvekillerinin toplandığı kurum"),
        ("EGEMENLİK", "Milletin kendi kendini yönetme hakkı"),
        ("GENÇLİK", "Cumhuriyeti koruyacak yeni kuşak"),
        ("İZMİR", "1922'de kurtarılan Ege kenti"),
        ("SAMSUN", "Atatürk'ün 19 Mayıs 1919'da çıktığı Karadeniz kenti"),
        ("ÇANAKKALE", "1915'te Atatürk'ün de savaştığı cephe"),
    ]),
    ("edebiyat", "Türk edebiyatı", [
        ("TANZİMAT", "1839'da başlayan yenileşme dönemi"),
        ("EDEBİYATICEDİDE", "Servet-i Fünun'un da bağlı olduğu yenilikçi akım"),
        ("VATAN", "Namık Kemal'in 1873'te sahnelenen oyunu"),
        ("AŞKIMEMNU", "Halit Ziya Uşaklıgil'in 1900'de yayımlanan romanı"),
        ("KUYUCAKLIYUSUF", "Sabahattin Ali'nin 1937'de yayımlanan romanı"),
        ("TUTUNAMAYANLAR", "Oğuz Atay'ın 1972'de yayımlanan romanı"),
        ("KÜRKMANTOLU", "Sabahattin Ali'nin 1943'te yayımlanan romanı"),
        ("GAZEL", "Aşk ve güzellik konulu klasik şiir biçimi"),
        ("KASİDE", "Övgü amaçlı klasik nazım biçimi"),
        ("ŞEYHGALİP", "Hüsn ü Aşk'ı yazan divan şairi"),
        ("YAHYAKEMAL", "Aruz vezniyle yazdığı şiirleriyle bilinen şair"),
        ("MESNEVİ", "Uzun, manzum hikâye biçimi"),
        ("FUZULİ", "Leyla ile Mecnun'u yazan şair"),
        ("NEDİM", "Lale Devri'nin ünlü şairi"),
        ("YUNUS", "Anadolu'nun büyük halk şairi"),
        ("DİVAN", "Eski şairlerin toplu eserleri"),
        ("ROMAN", "Uzun anlatılı kurmaca eser"),
        ("HİKAYE", "Kısa anlatılı kurmaca eser"),
        ("ÇALIKUŞU", "Reşat Nuri Güntekin'in ünlü romanı"),
        ("SİNEKLİBAKKAL", "Halide Edib Adıvar'ın 1936'da yayımlanan romanı"),
        ("İNCEMEMED", "Yaşar Kemal'in romanındaki ünlü kahraman"),
        ("TİYATRO", "Oyunların sahnelendiği sanat"),
        ("DERGİ", "Düzenli aralıklarla çıkan yayın"),
        ("EDEBİYAT", "Yazılı sanat eserlerinin genel adı"),
        ("ŞİİR", "Ölçülü ve uyaklı söz sanatı"),
        ("NAZIM", "Memleketimden İnsan Manzaraları'nı yazan şair"),
    ]),
    ("cografya", "Anadolu ve coğrafya", [
        ("KAÇKARDAĞLARI", "Karadeniz'in yüksek dağ sıralarından biri"),
        ("SÜPHAN", "Van Gölü'nün yakınındaki volkanik dağ"),
        ("EĞİRDİR", "Isparta'daki tatlı su gölü"),
        ("SAPANCA", "Sakarya'daki tatlı su gölü"),
        ("ULUDAĞ", "Bursa'daki ünlü kayak merkezi olan dağ"),
        ("GÖBEKLİTEPE", "Şanlıurfa'daki çok eski tapınak merkezi"),
        ("ÇATALHÖYÜK", "Konya'daki Neolitik yerleşim"),
        ("HATTUŞA", "Hitit başkenti"),
        ("PERGAMON", "Bergama'daki antik kent"),
        ("SARDES", "Manisa'daki antik Lidya kenti"),
        ("MUĞLA", "Fethiye'nin bağlı olduğu Ege ili"),
        ("SALDA", "Burdur'daki beyaz kumsallı göl"),
        ("KAPADOKYA", "Peri bacalarıyla ünlü bölge"),
        ("NEMRUT", "Adıyaman'daki dev heykelleriyle ünlü dağ"),
        ("ARARAT", "Doğu Anadolu'daki en yüksek dağ"),
        ("ERCİYES", "Kayseri'deki yüksek volkanik dağ"),
        ("TUZGÖLÜ", "Orta Anadolu'daki büyük tuzlu göl"),
        ("KIZILIRMAK", "Tamamen Türkiye'den akan en uzun nehir"),
        ("FIRAT", "Doğu'dan güneye akan uzun nehir"),
        ("MARMARA", "İstanbul'un bulunduğu iç deniz"),
        ("TROYA", "Çanakkale'deki antik kent"),
        ("EFES", "İzmir yakınındaki antik kent"),
        ("ANTALYA", "Akdeniz kıyısındaki turizm kenti"),
        ("TRABZON", "Karadeniz kıyısındaki kent"),
        ("BOĞAZ", "İki denizi birbirine bağlayan dar su yolu"),
        ("ANADOLU", "Asya'nın batısındaki geniş yarımada"),
        ("OVA", "Düz ve geniş tarım alanı"),
        ("DAĞ", "Yüksek ve sarp kara parçası"),
    ]),
    ("cicekler", "Çiçekler ve ağaçlar", [
        ("KAMELYA", "Kış aylarında açan, parlak yapraklı çiçek"),
        ("LAVANTA", "Kokulu, mor başaklı, kurutulan bitki"),
        ("ADAÇAYI", "Şifalı, kokulu bitki; çayı içilir"),
        ("KEKİK", "Kır yerlerinde yetişen baharatlık bitki"),
        ("SARMAŞIK", "Duvarlara tırmanan bitki"),
        ("MANOLYA", "Büyük, kokulu beyaz çiçek"),
        ("AYÇİÇEĞİ", "Sarı taçlı, tohumu kavrulan bitki"),
        ("FINDIK", "Karadeniz'de çok yetişen kabuklu yemiş"),
        ("FISTIK", "Gaziantep'in ünlü kabuklu yemişi"),
        ("BADEM", "İlkbaharda çiçek açan, kabuklu yemiş veren ağaç"),
        ("KİRAZ", "Erken yazda olgunlaşan kırmızı meyve"),
        ("KEÇİBOYNUZU", "Kurutulup un yapılan sert kabuklu meyve"),
        ("ISPANAK", "Yeşil yapraklı sebze"),
        ("PATLICAN", "Mor kabuklu sebze"),
        ("SÜMBÜL", "Kokusu güçlü, soğanlı çiçek"),
        ("NERGİS", "Kış sonunda açan beyaz çiçek"),
        ("LALE", "1718-1730 yılları arasında Osmanlı'da moda olan çiçek"),
        ("ÇINAR", "Gölgesi geniş, yapraklı ağaç"),
        ("ÇAM", "İğne yapraklı, hep yeşil ağaç"),
        ("ZEYTİN", "Ege'de yetişen, yağı bilinen ağaç"),
        ("MEŞE", "Palamut veren geniş yapraklı ağaç"),
        ("KAVAK", "Su kenarlarında yetişen uzun ağaç"),
        ("GÜL", "Dikenli dalları ve kokusuyla bilinen çiçek"),
        ("ZAMBAK", "Büyük ve beyaz çan biçimli çiçek"),
        ("ORKİDE", "Saksıda yetişen egzotik çiçek"),
        ("PAPATYA", "Beyaz yapraklı, sarı merkezli kır çiçeği"),
        ("LEYLAK", "Mayısta açan, kokulu mor çalı"),
    ]),
    ("hayvanlar", "Hayvanlar ve kuşlar", [
        ("AKBABA", "Leş yiyen büyük kuş"),
        ("FLAMİNGO", "Pembe tüylü, tek ayağı üzerinde duran kuş"),
        ("KİRPİ", "Dikenli, topaklanabilen küçük memeli"),
        ("SİNCAP", "Ağaçta yaşayan, kabarık kuyruklu kemirgen"),
        ("DENİZATI", "Dik duran, küçük deniz canlısı"),
        ("AHTAPOT", "Sekiz kollu deniz canlısı"),
        ("YUNUSBALIĞI", "Akıllı ve oyunbaz deniz memelisi"),
        ("KURBAĞA", "Hem karada hem suda yaşayan hayvan"),
        ("PAPAĞAN", "Renkli tüylü, konuşabilen kuş"),
        ("ŞAHİN", "Hızlı avlanan yırtıcı kuş"),
        ("KELEBEK", "Renkli kanatlı, çiçeklerde gezen böcek"),
        ("ÇEKİRGE", "Sıçrayarak hareket eden ot böceği"),
        ("AKREP", "Kuyruğunda zehirli iğnesi olan"),
        ("ÖRÜMCEK", "Ağ örüp avını yakalayan"),
        ("TİLKİ", "Kızıl kürklü, kurnaz hayvan"),
        ("ÇAKAL", "Tilkiye benzeyen yabani hayvan"),
        ("EŞEK", "Yük taşımada kullanılan hayvan"),
        ("KAPLUMBAĞA", "Sert kabuklu, yavaş sürüngen"),
        ("KERTENKELE", "Güneşlenmeyi seven, kuyruğunu kopartabilen sürüngen"),
        ("YARASA", "Gece uçan memeli"),
        ("MARTI", "Deniz kıyısında yaşayan, denizde uçan kuş"),
        ("LEYLEK", "Göç eden, uzun bacaklı kuş"),
        ("KARTAL", "Yüksekte uçan, güçlü yırtıcı kuş"),
        ("BÜLBÜL", "Güzel ötüşüyle bilinen küçük kuş"),
        ("KAPLAN", "Çizgili, büyük yırtıcı kedi"),
        ("KURT", "Sürü halinde yaşayan yabani köpek"),
        ("BALIK", "Suda yaşayan, solungaçlı hayvan"),
    ]),
    ("mutfak", "Türk mutfağı", [
        ("KUNEFE", "Peynirli, şerbetli tatlı"),
        ("ŞİŞKEBAP", "Şişe dizilip pişirilen et yemeği"),
        ("KADAYIF", "İnce ipli, şerbetli hamur işi"),
        ("LOKMA", "Şerbetli küçük tatlı"),
        ("HELVA", "Un ya da tahinle yapılan tatlı"),
        ("TARHANA", "Yoğurt ve undan yapılıp kurutulan karışım"),
        ("ÇILBIR", "Yoğurtlu, yumurtalı kahvaltılık"),
        ("MUHALLEBİ", "Sütlü, nişastalı tatlı"),
        ("TULUMBA", "Şerbetli, spiral biçimli tatlı"),
        ("ZEYTİNYAĞI", "Ege'nin temel yağı"),
        ("SUCUK", "Baharatlı kurutulmuş sosis"),
        ("PASTIRMA", "Kuru etle yapılan, baharatlı et ürünü"),
        ("KAVURMA", "Yağda kavrulan et yemeği"),
        ("KIYMA", "Öğütülmüş et"),
        ("İMAMBAYILDI", "Zeytinyağlı, patlıcanlı bir yemek"),
        ("MERCİMEK", "Kırmızı ya da yeşil bir bakliyat"),
        ("BAKLAVA", "Fıstıklı, şerbetli tatlı"),
        ("GÖZLEME", "Yufkaya sarılarak sacda pişirilen yemek"),
        ("SİMİT", "Susamlı, halka şeklinde hamur işi"),
        ("TURŞU", "Sirkeli sularda saklanan sebze"),
        ("REÇEL", "Meyveden şekerle yapılan kahvaltılık"),
        ("PEYNİR", "Sütten yapılan, kahvaltının vazgeçilmezi"),
        ("YOĞURT", "Sütten mayalanarak yapılan süt ürünü"),
        ("MANTI", "Küçük hamur parçalarının yoğurtla servis edildiği yemek"),
        ("BÖREK", "Yufka hamurundan yapılan hamur işi"),
        ("PİLAV", "Pirinçten yapılan, yemeklerin yanında servis edilen"),
        ("ÇORBA", "Sıvı yemek, genellikle başlangıçta içilir"),
        ("KAYMAK", "Sütün üstünde oluşan yağlı tabaka"),
    ]),
    ("okul", "Dil ve okul bilgisi", [
        ("AYDINLANMA", "Akıl ve bilimi öne çıkaran 18. yüzyıl düşünce akımı"),
        ("OKURYAZAR", "Okuyup yazabilen kişi"),
        ("ÖĞRENCİ", "Öğrenim gören kişi"),
        ("DİKTE", "Öğrencilere yazdırılan metin"),
        ("MÜFREDAT", "Derslerin içeriğini belirleyen program"),
        ("KÜTÜPHANE", "Kitapların düzenli tutulduğu yer"),
        ("ENSTİTÜ", "Üniversitede ihtisas birimi"),
        ("SEMİNER", "Bir konu üzerine yapılan toplu tartışma"),
        ("MUALLİM", "Eski dilde öğretmen"),
        ("KARALAMA", "Taslak niteliğinde hızlı çizim"),
        ("HECE", "Tek bir ünlü sesle oluşan ses birimi"),
        ("SÖZCÜK", "Anlamı olan harf dizisi"),
        ("CÜMLE", "Yüklem içeren anlam birimi"),
        ("NOKTALAMA", "Yazıya anlam veren işaretlerin kullanımı"),
        ("DİLBİLGİSİ", "Dilin kurallarını inceleyen bilim"),
        ("ÖZNE", "Cümlede işi yapan ya da hakkında konuşulan"),
        ("YÜKLEM", "Cümlenin fiil içeren kısmı"),
        ("DEFTER", "Yazı yazmak için kullanılan sayfalı kitapçık"),
        ("KALEM", "Yazı yazmaya yarayan araç"),
        ("SİLGİ", "Yanlış yazılanı silmeye yarayan araç"),
        ("CETVEL", "Düz çizgi çizmeye yarayan araç"),
        ("ÖĞRETMEN", "Dersi anlatan kişi"),
        ("TEBEŞİR", "Tahtaya yazı yazmakta kullanılan çubuk"),
        ("TENEFFÜS", "Dersler arasındaki kısa mola"),
        ("ÖDEV", "Evde yapılması istenen çalışma"),
        ("KARNE", "Yıl sonunda verilen not belgesi"),
        ("DERS", "Belirli bir konunun öğretildiği saat"),
        ("ZİL", "Ders başladığını bildiren ses"),
    ]),
    ("mevsim", "Gökyüzü, zaman ve takvim", [
        ("GÖKBİLİM", "Gök cisimlerini inceleyen bilim"),
        ("YARIYIL", "Akademik takvimde altı aylık dönem"),
        ("ARTIYIL", "Şubat'a bir gün eklenen yıl"),
        ("RAMAZAN", "Oruç tutulan ay"),
        ("HİCRİ", "Ay takvimine dayanan takvim"),
        ("MİLADİ", "Hz. İsa'nın doğumuna dayanan takvim"),
        ("ŞAFAK", "Güneş doğmadan önceki gökyüzü ışığı"),
        ("GÜNBATIMI", "Güneşin ufukta kaybolduğu an"),
        ("DOLUNAY", "Tam daire görünen ay"),
        ("GECEYARISI", "Gece on ikiyi gösteren an"),
        ("GÖKKUŞAĞI", "Yağmurdan sonra çıkan renkli kavis"),
        ("GÖKGÜRÜLTÜ", "Şimşekle birlikte duyulan ses"),
        ("ŞİMŞEK", "Gökte çakan elektrik"),
        ("SİS", "Havada asılı kalan ince bulut"),
        ("FIRTINA", "Şiddetli rüzgar ve yağış"),
        ("ÇİĞ", "Sabah otların üstünde biriken su taneleri"),
        ("KURAK", "Yağışın az olduğu dönem"),
        ("SEL", "Aşırı yağıştan taşan su"),
        ("TAKVİM", "Günleri ve ayları gösteren liste"),
        ("OCAK", "Yılın ilk ayı"),
        ("ŞUBAT", "Kısa ve soğuk ay"),
        ("TEMMUZ", "Yılın en sıcak aylarından biri"),
        ("EYLÜL", "Yaz bitiminde gelen ay"),
        ("GÜNEŞ", "Dünyaya ışık ve ısı veren yıldız"),
        ("RÜZGAR", "Havanın hareket etmesiyle oluşan akım"),
        ("YAĞMUR", "Gökten düşen su damlaları"),
        ("İLKBAHAR", "Kışın ardından gelen mevsim"),
        ("SONBAHAR", "Yaprakların döküldüğü mevsim"),
    ]),
    ("elsanatlari", "El sanatları", [
        ("NAKIŞ", "İğne ile kumaşa işlenen süsleme"),
        ("ÖRGÜ", "Şişle ilmek ilmek yapılan giysi ya da örtü"),
        ("YAZMA", "Bursa'da ünlü, desenli el işi kumaş"),
        ("KİLİM", "Yüzeyi düz dokunan yer halısı"),
        ("ÇİNİ", "Fırınlanmış, renkli, süslü seramik"),
        ("DOKUMA", "Tezgâhta iplikle kumaş yapma"),
        ("MAKRAME", "Düğümlerle yapılan süs örgüsü"),
        ("ÇEYİZ", "Gelin hazırlığında hazırlanan eşyalar"),
        ("İĞNE", "Dikiş yapmaya yarayan ince metal"),
        ("İPLİK", "Dokumada kullanılan ince lif"),
        ("SEPET", "Hasır örgüden yapılan taşıma kabı"),
        ("KEÇE", "Yünün sıkıştırılmasıyla yapılan kumaş"),
        ("HASIR", "Kamıştan örülen dayanıklı mat"),
        ("OYA", "İğne ile ipten yapılan dantel"),
        ("TEZGAH", "Dokuma yapılan alet"),
        ("EBRU", "Suya boyayla desen oluşturma sanatı"),
        ("TEZHİP", "Kitap süslemesinde altın kullanma sanatı"),
        ("HATTAT", "Güzel yazı sanatında usta kişi"),
        ("MİNYATÜR", "Küçük boyutlu, ayrıntılı resim sanatı"),
        ("MOZAİK", "Renkli taş parçalarıyla yapılan resim"),
        ("SEDEF", "Kakma işinde kullanılan parlak madde"),
        ("KAKMA", "Sedef ve kemik parçalarıyla yapılan süsleme"),
        ("BAKIR", "Dövülerek işlenen kırmızımsı metal"),
    ]),
    ("genel", "Bilim, tarih ve sanat", [
        ("ORTAÇAĞ", "Antik çağ ile Rönesans arasındaki dönem"),
        ("OSMANLI", "Altı yüzyıl süren imparatorluk"),
        ("BİZANS", "Doğu Roma İmparatorluğu"),
        ("SELÇUKLU", "Malazgirt ile Anadolu'ya giren Türk devleti"),
        ("KEŞİF", "Yeni yer bulma işi"),
        ("MİMARSİNAN", "Süleymaniye Camii'nin mimarı"),
        ("HEZARFEN", "Galata Kulesi'nden uçtuğu rivayet edilen"),
        ("LEONARDO", "Mona Lisa'yı yapan ressam"),
        ("BEETHOVEN", "Dokuzuncu Senfoni'nin bestecisi"),
        ("EINSTEIN", "Görelilik kuramını ortaya atan fizikçi"),
        ("NEWTON", "Yerçekimini açıklayan bilim insanı"),
        ("KOPERNİK", "Güneş merkezli evreni öneren astronom"),
        ("GALİLE", "Teleskopla gözlem yapan İtalyan bilim insanı"),
        ("NOTA", "Müzikte sesleri gösteren işaret"),
        ("KEMAN", "Yaylı çalgı"),
        ("NEY", "Kamışla çalınan üflemeli çalgı"),
        ("BAĞLAMA", "Telli, Anadolu'nun halk çalgısı"),
        ("KANUN", "Tellerine tokmakla vurulan çalgı"),
        ("SENFONİ", "Orkestra için büyük müzik eseri"),
        ("BESTE", "Yeni bir müzik eseri"),
        ("TEMPO", "Müziğin hızı"),
        ("KOMPOZİTÖR", "Müzik eseri yazan kişi"),
        ("HEYKELTIRAŞ", "Heykel yapan sanatçı"),
        ("MİMARİ", "Yapı sanatı"),
        ("SAHNE", "Tiyatro oyununun oynandığı yer"),
        ("RESSAM", "Tablo yapan sanatçı"),
        ("HEYKEL", "Taştan ya da bronzdan yapılan üç boyutlu eser"),
        ("MÜZE", "Eserlerin sergilendiği yer"),
        ("ORKESTRA", "Birlikte çalan müzisyen topluluğu"),
        ("OPERA", "Müziğin ağırlıkta olduğu sahne sanatı"),
        ("SİNEMA", "Filmlerin gösterildiği yer"),
    ]),
]


def check_words(entries):
    for answer, clue in entries:
        if not answer or not all(ch.isalpha() for ch in answer):
            raise ValueError("Geçersiz cevap: %r" % answer)
        if answer != answer.upper():
            raise ValueError("Cevap büyük harf olmalı: %r" % answer)
        if not (3 <= len(answer) <= 15):
            raise ValueError("Uzunluk dışı cevap: %r" % answer)
        if not clue.strip():
            raise ValueError("Boş ipucu: %r" % answer)


def compile_engine(workdir):
    javac = shutil.which("javac")
    java = shutil.which("java")
    if not javac or not java:
        sys.exit("javac/java bulunamadı. JDK 17+ kurulu olmalı.")
    subprocess.run([javac, "-encoding", "UTF-8", "-d", workdir, ENGINE_SRC, CHECK_SRC],
                   check=True)
    return java


def count_placed(java, workdir, blocks):
    lines = []
    for i, block in enumerate(blocks):
        if i:
            lines.append("---")
        for answer, clue in block:
            lines.append("%s|%s" % (answer, clue.replace("|", "/")))
    result = subprocess.run([java, "-Dfile.encoding=UTF-8", "-cp", workdir, "BankCheck"],
                            input="\n".join(lines) + "\n", capture_output=True,
                            text=True, encoding="utf-8", check=True)
    counts = [int(x) for x in result.stdout.split()]
    if len(counts) != len(blocks):
        raise RuntimeError("Beklenmeyen çıktı sayısı")
    return counts


def pick_disjoint(rng, java, workdir, pool, used, min_placed, wanted):
    """Havuzdan, daha önce kullanılmamış kelimelerle kurulan bulmacaları seçer."""
    chosen = []
    while len(chosen) < wanted:
        avail = [w for w in pool if w[0] not in used]
        if len(avail) < SUBSET_MIN:
            break
        candidates = []
        for _ in range(CANDIDATES_PER_TOPIC):
            k = rng.randint(SUBSET_MIN, min(SUBSET_MAX, len(avail)))
            candidates.append(rng.sample(avail, k))
        counts = count_placed(java, workdir, candidates)
        scored = [c for c, n in zip(candidates, counts) if n >= min_placed]
        if not scored:
            break
        rng.shuffle(scored)
        progress = False
        for subset in scored:
            if len(chosen) >= wanted:
                break
            if any(a in used for a, _ in subset):
                continue
            chosen.append(subset)
            used.update(a for a, _ in subset)
            progress = True
        if not progress:
            break
    return chosen


def load_extra(key):
    path = os.path.join(WORDLIST_DIR, key + ".txt")
    items = []
    if not os.path.exists(path):
        return items
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            answer, clue = line.split("|", 1)
            items.append((answer.strip(), clue.strip()))
    return items


def main():
    rng = random.Random(20261105)
    workdir = tempfile.mkdtemp(prefix="cengel_check_")
    puzzles = []
    report = []
    used = set()
    seen = set()
    merged = []
    for key, title, pool in TOPICS:
        items = []
        for a, c in list(pool) + load_extra(key):
            if a in seen:
                continue
            seen.add(a)
            items.append((a, c))
        check_words(items)
        merged.append((key, title, items))
    try:
        java = compile_engine(workdir)
        for key, title, pool in merged:
            chosen = pick_disjoint(rng, java, workdir, pool, used, MIN_PLACED_PREFERRED,
                                   PUZZLES_PER_TOPIC)
            if len(chosen) < PUZZLES_PER_TOPIC:
                more = pick_disjoint(rng, java, workdir, pool, used, MIN_PLACED_FALLBACK,
                                     PUZZLES_PER_TOPIC - len(chosen))
                chosen.extend(more)
            for i, subset in enumerate(chosen, start=1):
                puzzles.append({
                    "id": "%s-%s-%03d" % (ID_PREFIX, key, i),
                    "topic": title,
                    "words": [{"answer": a, "clue": c} for a, c in subset],
                })
            left = sum(1 for a, _ in pool if a not in used)
            report.append((title, len(chosen), len(pool), left))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    bank = {"version": BANK_VERSION, "puzzles": puzzles}
    text = json.dumps(bank, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(ASSET_OUT), exist_ok=True)
    with open(ASSET_OUT, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open(ROOT_OUT, "w", encoding="utf-8") as f:
        f.write(text + "\n")

    for title, n, pool_size, left in report:
        print("%-28s %3d bulmaca (havuz: %d kelime, kullanılmayan: %d)" % (title, n, pool_size, left))
    print("Toplam: %d bulmaca, sürüm %s -> %s" % (len(puzzles), BANK_VERSION, ASSET_OUT))


if __name__ == "__main__":
    main()
