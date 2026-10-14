from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import json, os, sqlite3, secrets, hashlib, hmac, base64, re, mimetypes, html

ROOT = Path(__file__).resolve().parent
# Dedicated v8 database; migrate from a neighboring older GeoJoy project without altering the source database.
DB_PATH = ROOT / 'geojoy_v8.db'
APP_VERSION = '8.9.0'
UPLOADS = ROOT / 'uploads'
UPLOADS.mkdir(exist_ok=True)
STATIC_DIR = ROOT / 'static'
STATIC_ASSETS = frozenset({'styles.css', 'app.js', 'admin.css', 'admin.js', 'geojoy-favicon.svg'})
ADMIN_PASSWORD = os.environ.get('GEOJOY_ADMIN_PASSWORD', 'GeoJoy2026!')
COOKIE_SECURE = os.environ.get('GEOJOY_COOKIE_SECURE', '').strip().lower() in {'1', 'true', 'yes', 'on'}
COOKIE_SECURE_SUFFIX = '; Secure' if COOKIE_SECURE else ''
SESSIONS = set()
RECOVERY_FAILURES = {}
PASSWORD_HASH_ITERATIONS = 240_000
MIN_PASSWORD_LENGTH = 10

# Location-specific Georgia photographs are sourced from Wikimedia Commons; see /photo-credits.
SEED = json.loads(r'''{
  "brand": {
    "name": "GeoJoy",
    "logo": ""
  },
  "defaultLanguage": "ka",
  "heroSlides": [
    {
      "image": "/uploads/geojoy_heroslides_01.webp",
      "title": {
        "ka": "ძველი თბილისის ხიბლი",
        "en": "The charm of Old Tbilisi",
        "ru": "Очарование старого Тбилиси",
        "ar": "سحر تبليسي القديمة"
      },
      "subtitle": {
        "ka": "აივნები, ძველი ქუჩები და ქალაქის გამორჩეული ხედები.",
        "en": "Balconies, old streets, and unforgettable city views.",
        "ru": "Балконы, старые улицы и незабываемые виды города.",
        "ar": "شرفات وشوارع قديمة وإطلالات لا تُنسى."
      },
      "imagePosition": "50% 54%"
    },
    {
      "image": "/uploads/geojoy_heroslides_02.webp",
      "title": {
        "ka": "ბათუმი და შავი ზღვის სანაპირო",
        "en": "Batumi and the Black Sea coast",
        "ru": "Батуми и побережье Чёрного моря",
        "ar": "باتومي وساحل البحر الأسود"
      },
      "subtitle": {
        "ka": "ზღვისპირა ბულვარი და აჭარის სანაპიროს ხასიათი.",
        "en": "The seaside boulevard and the spirit of Adjara.",
        "ru": "Приморский бульвар и атмосфера Аджарии.",
        "ar": "الكورنيش البحري وأجواء أجارا."
      },
      "imagePosition": "50% 52%"
    },
    {
      "image": "/uploads/geojoy_heroslides_03.webp",
      "title": {
        "ka": "სვანეთის კოშკები და კავკასიონი",
        "en": "Svan towers and the Caucasus",
        "ru": "Сванские башни и Кавказ",
        "ar": "أبراج سفانيتي وجبال القوقاز"
      },
      "subtitle": {
        "ka": "მესტიის ისტორიული კოშკები მთების ფონზე.",
        "en": "Historic towers of Mestia framed by mountain scenery.",
        "ru": "Исторические башни Местии на фоне гор.",
        "ar": "أبراج ميستيا التاريخية وسط مشاهد الجبال."
      },
      "imagePosition": "54% 47%"
    },
    {
      "image": "/uploads/geojoy_heroslides_04.webp",
      "title": {
        "ka": "ყაზბეგი და გერგეტის სამება",
        "en": "Kazbegi and Gergeti Trinity Church",
        "ru": "Казбеги и Гергетская Троица",
        "ar": "كازبيغي وكنيسة غيرغيتي"
      },
      "subtitle": {
        "ka": "კავკასიონის მთები და საქართველოს ერთ-ერთი ყველაზე ცნობილი ტაძარი.",
        "en": "Caucasus mountains and one of Georgia’s best-known churches.",
        "ru": "Кавказские горы и один из самых известных храмов Грузии.",
        "ar": "جبال القوقاز وواحدة من أشهر كنائس جورجيا."
      },
      "imagePosition": "58% 52%"
    },
    {
      "image": "/uploads/geojoy_heroslides_05.webp",
      "title": {
        "ka": "გუდაური — მთის ხედები",
        "en": "Gudauri mountain views",
        "ru": "Гудаури — горные виды",
        "ar": "غوداوري وإطلالات الجبال"
      },
      "subtitle": {
        "ka": "მცხეთა-მთიანეთის ალპური პეიზაჟები და სამთო კურორტი.",
        "en": "Alpine landscapes and a mountain resort in Mtskheta-Mtianeti.",
        "ru": "Альпийские пейзажи и горный курорт Мцхета-Мтианети.",
        "ar": "مناظر جبلية ومنتجع في متسخيتا-متيانيتي."
      },
      "imagePosition": "50% 55%"
    },
    {
      "image": "/uploads/geojoy_heroslides_06.webp",
      "title": {
        "ka": "მარტვილის კანიონის მწვანე ხეობა",
        "en": "The green gorge of Martvili Canyon",
        "ru": "Зелёное ущелье каньона Мартвили",
        "ar": "الوادي الأخضر في مارتفيلي"
      },
      "subtitle": {
        "ka": "სამეგრელოს წყალი, კლდეები და სიმწვანე.",
        "en": "Water, cliffs, and lush scenery in Samegrelo.",
        "ru": "Вода, скалы и зелёные пейзажи Самегрело.",
        "ar": "المياه والمنحدرات والطبيعة الخضراء في سامغريلو."
      },
      "imagePosition": "50% 50%"
    },
    {
      "image": "/uploads/geojoy_heroslides_07.webp",
      "title": {
        "ka": "კახეთის ფერადი აივნები",
        "en": "The colorful streets of Kakheti",
        "ru": "Яркие улочки Кахетии",
        "ar": "شوارع كاخيتي الملونة"
      },
      "subtitle": {
        "ka": "სიღნაღის ხედები ალაზნის ველისკენ.",
        "en": "Views from Sighnaghi toward the Alazani Valley.",
        "ru": "Виды из Сигнахи на Алазанскую долину.",
        "ar": "إطلالات سيغناغي نحو وادي ألازاني."
      },
      "imagePosition": "50% 48%"
    },
    {
      "image": "/uploads/geojoy_heroslides_08.webp",
      "title": {
        "ka": "ვარძია — კლდეში ნაკვეთი ქალაქი",
        "en": "Vardzia, the cave city",
        "ru": "Вардзия — пещерный город",
        "ar": "فاردزيا، مدينة الكهوف"
      },
      "subtitle": {
        "ka": "სამცხე-ჯავახეთის ისტორია კლდის ფერდობზე.",
        "en": "Samtskhe-Javakheti history carved into the rock.",
        "ru": "История Самцхе-Джавахети, высеченная в скале.",
        "ar": "تاريخ سامتسخه-جافاخيتي المنحوت في الصخر."
      },
      "imagePosition": "50% 50%"
    },
    {
      "image": "/uploads/geojoy_heroslides_09.webp",
      "title": {
        "ka": "ბორჯომის მწვანე ბილიკები",
        "en": "The green paths of Borjomi",
        "ru": "Зелёные тропы Боржоми",
        "ar": "الممرات الخضراء في بورجومي"
      },
      "subtitle": {
        "ka": "დასვენება ბუნებაში, ტყის ბილიკები და სუფთა ჰაერი.",
        "en": "Nature, forest paths, and fresh mountain air.",
        "ru": "Природа, лесные тропы и свежий горный воздух.",
        "ar": "الطبيعة ومسارات الغابات والهواء الجبلي النقي."
      },
      "imagePosition": "50% 48%"
    },
    {
      "image": "/uploads/geojoy_heroslides_10.webp",
      "title": {
        "ka": "დაშბაშის კანიონი",
        "en": "Dashbashi Canyon",
        "ru": "Каньон Дашбаши",
        "ar": "وادي داشباشي"
      },
      "subtitle": {
        "ka": "ქვემო ქართლის გამორჩეული ბუნებრივი ძეგლი.",
        "en": "A remarkable natural landmark in Kvemo Kartli.",
        "ru": "Примечательный природный памятник Квемо-Картли.",
        "ar": "معلم طبيعي مميز في كفيمو كارتلي."
      },
      "imagePosition": "50% 48%"
    }
  ],
  "regions": [
    {
      "id": "tbilisi",
      "name": {
        "ka": "თბილისი",
        "en": "Tbilisi",
        "ru": "Тбилиси",
        "ar": "تبليسي"
      },
      "description": {
        "ka": "ძველი ქუჩები, აივნები, კულტურა და თანამედროვე ქალაქის ენერგია.",
        "en": "Old streets, balconies, culture, and modern city energy.",
        "ru": "Старые улицы, балконы, культура и энергия современного города.",
        "ar": "شوارع قديمة وشرفات وثقافة وروح مدينة حديثة."
      },
      "image": "/uploads/geojoy_regions_tbilisi_dusk.webp",
      "imagePosition": "50% 52%"
    },
    {
      "id": "adjara",
      "name": {
        "ka": "აჭარა",
        "en": "Adjara",
        "ru": "Аджария",
        "ar": "أجاريا"
      },
      "description": {
        "ka": "შავი ზღვა, ბათუმი და მწვანე მთები.",
        "en": "The Black Sea, Batumi, and green mountains.",
        "ru": "Чёрное море, Батуми и зелёные горы.",
        "ar": "البحر الأسود وباتومي والجبال الخضراء."
      },
      "image": "/uploads/geojoy_regions_12.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "svaneti",
      "name": {
        "ka": "სვანეთი",
        "en": "Svaneti",
        "ru": "Сванетия",
        "ar": "سفانيتي"
      },
      "description": {
        "ka": "კავკასიონის ხედები, კოშკები და მთის ბილიკები.",
        "en": "Caucasus views, historic towers, and mountain trails.",
        "ru": "Виды Кавказа, исторические башни и горные тропы.",
        "ar": "مناظر القوقاز والأبراج التاريخية ومسارات الجبال."
      },
      "image": "/uploads/geojoy_regions_13.webp",
      "imagePosition": "50% 48%"
    },
    {
      "id": "kakheti",
      "name": {
        "ka": "კახეთი",
        "en": "Kakheti",
        "ru": "Кахетия",
        "ar": "كاخيتي"
      },
      "description": {
        "ka": "ვენახები, ღვინის ტრადიციები და ფართო ველები.",
        "en": "Vineyards, wine traditions, and wide-open landscapes.",
        "ru": "Виноградники, винные традиции и просторные пейзажи.",
        "ar": "كروم العنب وتقاليد النبيذ والمناظر الواسعة."
      },
      "image": "/uploads/geojoy_regions_14.webp",
      "imagePosition": "50% 48%"
    },
    {
      "id": "imereti",
      "name": {
        "ka": "იმერეთი",
        "en": "Imereti",
        "ru": "Имеретия",
        "ar": "إيميريتي"
      },
      "description": {
        "ka": "მწვანე ბუნება, ისტორიული ადგილები და სტუმართმოყვარეობა.",
        "en": "Green landscapes, historic places, and warm hospitality.",
        "ru": "Зелёная природа, исторические места и гостеприимство.",
        "ar": "طبيعة خضراء وأماكن تاريخية وكرم الضيافة."
      },
      "image": "/uploads/geojoy_regions_15.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "guria",
      "name": {
        "ka": "გურია",
        "en": "Guria",
        "ru": "Гурия",
        "ar": "غوريا"
      },
      "description": {
        "ka": "ჩაის კულტურა, ზღვისპირეთი და მწვანე ბორცვები.",
        "en": "Tea culture, coastline, and green hills.",
        "ru": "Чайная культура, побережье и зелёные холмы.",
        "ar": "ثقافة الشاي والساحل والتلال الخضراء."
      },
      "image": "/uploads/geojoy_regions_16.webp",
      "imagePosition": "50% 48%"
    },
    {
      "id": "samegrelo",
      "name": {
        "ka": "სამეგრელო",
        "en": "Samegrelo",
        "ru": "Самегрело",
        "ar": "سامغريلو"
      },
      "description": {
        "ka": "კულტურა, ბუნება და ადგილობრივი გემოები.",
        "en": "Culture, nature, and local flavors.",
        "ru": "Культура, природа и местные вкусы.",
        "ar": "الثقافة والطبيعة والنكهات المحلية."
      },
      "image": "/uploads/geojoy_regions_17.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "racha",
      "name": {
        "ka": "რაჭა",
        "en": "Racha",
        "ru": "Рача",
        "ar": "راتشا"
      },
      "description": {
        "ka": "მშვიდი მთები, ტბები და ბუნების სილამაზე.",
        "en": "Quiet mountains, lakes, and beautiful landscapes.",
        "ru": "Тихие горы, озёра и красивые пейзажи.",
        "ar": "جبال هادئة وبحيرات ومناظر طبيعية جميلة."
      },
      "image": "/uploads/geojoy_regions_18.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "mtskheta",
      "name": {
        "ka": "მცხეთა-მთიანეთი",
        "en": "Mtskheta-Mtianeti",
        "ru": "Мцхета-Мтианети",
        "ar": "متسخيتا-متيانيتي"
      },
      "description": {
        "ka": "უძველესი კულტურა და მთისკენ მიმავალი გზები.",
        "en": "Ancient heritage and roads leading into the mountains.",
        "ru": "Древнее наследие и дороги в горы.",
        "ar": "تراث عريق وطرق تقود إلى الجبال."
      },
      "image": "/uploads/geojoy_regions_19.webp",
      "imagePosition": "50% 52%"
    },
    {
      "id": "samtskhe",
      "name": {
        "ka": "სამცხე-ჯავახეთი",
        "en": "Samtskhe-Javakheti",
        "ru": "Самцхе-Джавахети",
        "ar": "سام츠خე-جافاخيتي"
      },
      "description": {
        "ka": "ციხესიმაგრეები, ტბები და ისტორიული მემკვიდრეობა.",
        "en": "Fortresses, lakes, and historic heritage.",
        "ru": "Крепости, озёра и историческое наследие.",
        "ar": "قلاع وبحيرات وتراث تاريخي."
      },
      "image": "/uploads/geojoy_regions_20.webp",
      "imagePosition": "50% 48%"
    },
    {
      "id": "kvemo",
      "name": {
        "ka": "ქვემო ქართლი",
        "en": "Kvemo Kartli",
        "ru": "Квемо-Картли",
        "ar": "كفيمو كارتلي"
      },
      "description": {
        "ka": "მრავალფეროვანი ისტორია და ბუნებრივი ხედები.",
        "en": "Layered history and varied landscapes.",
        "ru": "Многослойная история и разнообразные пейзажи.",
        "ar": "تاريخ متنوع ومناظر طبيعية مختلفة."
      },
      "image": "/uploads/geojoy_regions_21.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "shida",
      "name": {
        "ka": "შიდა ქართლი",
        "en": "Shida Kartli",
        "ru": "Шида-Картли",
        "ar": "شيدا كارتلي"
      },
      "description": {
        "ka": "ისტორიული ადგილები და ქართული სოფლის ხედები.",
        "en": "Historic places and Georgian countryside.",
        "ru": "Исторические места и грузинская сельская местность.",
        "ar": "أماكن تاريخية وريف جورجي."
      },
      "image": "/uploads/geojoy_regions_22.webp",
      "imagePosition": "50% 50%"
    }
  ],
  "tours": [
    {
      "id": "geo01",
      "name": {
        "ka": "თბილისის ძველი ქალაქი",
        "en": "Old Tbilisi Walking Tour",
        "ru": "Пешая экскурсия по старому Тбилиси",
        "ar": "جولة في تبليسي القديمة"
      },
      "description": {
        "ka": "ძველი თბილისი, აბანოთუბანი, ნარიყალა და ქალაქის ისტორიული ქუჩები.",
        "en": "Old Tbilisi Walking Tour. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Пешая экскурсия по старому Тбилиси. Знакомство с местными достопримечательностями и природой.",
        "ar": "جولة في تبليسي القديمة. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "tbilisi",
      "image": "/uploads/geojoy_tours_23.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo03",
      "name": {
        "ka": "ბათუმი და შავი ზღვის სანაპირო",
        "en": "Batumi & Black Sea Coast",
        "ru": "Батуми и побережье Чёрного моря",
        "ar": "باتومي وساحل البحر الأسود"
      },
      "description": {
        "ka": "ბათუმის ბულვარი, ძველი ბათუმი და შავი ზღვის სანაპირო.",
        "en": "Batumi & Black Sea Coast. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Батуми и побережье Чёрного моря. Знакомство с местными достопримечательностями и природой.",
        "ar": "باتومي وساحل البحر الأسود. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "adjara",
      "image": "/uploads/geojoy_tours_24.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo04",
      "name": {
        "ka": "მთიანი აჭარა და მახუნცეთის ჩანჩქერი",
        "en": "Mountainous Adjara & Makhuntseti",
        "ru": "Горная Аджария и водопад Махунцети",
        "ar": "أجاريا الجبلية وشلال ماخونتسي"
      },
      "description": {
        "ka": "მწვანე ხეობები, მახუნცეთის ჩანჩქერი და ქვის თაღოვანი ხიდი.",
        "en": "Mountainous Adjara & Makhuntseti. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Горная Аджария и водопад Махунцети. Знакомство с местными достопримечательностями и природой.",
        "ar": "أجاريا الجبلية وشلال ماخونتسي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "adjara",
      "image": "/uploads/geojoy_tours_25.webp",
      "imagePosition": "50% 36%",
      "imageFit": "contain"
    },
    {
      "id": "geo05",
      "name": {
        "ka": "გურიის მწვანე სოფლები და ჩაის ისტორია",
        "en": "Green Guria & Tea Heritage",
        "ru": "Зелёная Гурия и чайные традиции",
        "ar": "غوريا الخضراء وتراث الشاي"
      },
      "description": {
        "ka": "გურიის სოფლების, ჩაის კულტურისა და ბუნების გაცნობა.",
        "en": "Green Guria & Tea Heritage. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Зелёная Гурия и чайные традиции. Знакомство с местными достопримечательностями и природой.",
        "ar": "غوريا الخضراء وتراث الشاي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "guria",
      "image": "/uploads/geojoy_tours_26.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo06",
      "name": {
        "ka": "მარტვილის კანიონი და დადიანების სასახლე",
        "en": "Martvili Canyon & Dadiani Palace",
        "ru": "Каньон Мартвили и дворец Дадиани",
        "ar": "وادي مارتفيلي وقصر دادياني"
      },
      "description": {
        "ka": "მარტვილის კანიონის ბუნება და ზუგდიდის ისტორიული მემკვიდრეობა.",
        "en": "Martvili Canyon & Dadiani Palace. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Каньон Мартвили и дворец Дадиани. Знакомство с местными достопримечательностями и природой.",
        "ar": "وادي مارتفيلي وقصر دادياني. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "samegrelo",
      "image": "/uploads/geojoy_tours_27.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo07",
      "name": {
        "ka": "ოკატეს კანიონი",
        "en": "Okatse Canyon",
        "ru": "Каньон Окаце",
        "ar": "وادي أوكاتسي"
      },
      "description": {
        "ka": "იმერეთის ტყიანი კანიონი და მისი საფეხმავლო ბილიკები.",
        "en": "Explore Imereti’s forested canyon and its walking trails.",
        "ru": "Лесистый каньон Имерети и его пешеходные тропы.",
        "ar": "استكشف الوادي الحراجي ومسارات المشي في إيميريتي."
      },
      "region": "imereti",
      "image": "/uploads/geojoy_tours_28.webp",
      "imagePosition": "50% 48%"
    },
    {
      "id": "geo08",
      "name": {
        "ka": "მესტია და სვანური კოშკები",
        "en": "Mestia & Svan Towers",
        "ru": "Местия и сванские башни",
        "ar": "ميستيا وأبراج سفانيتي"
      },
      "description": {
        "ka": "მესტიის ისტორიული ცენტრი და სვანური თავდაცვითი კოშკები.",
        "en": "Mestia & Svan Towers. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Местия и сванские башни. Знакомство с местными достопримечательностями и природой.",
        "ar": "ميستيا وأبراج سفانيتي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "svaneti",
      "image": "/uploads/geojoy_tours_29.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo09",
      "name": {
        "ka": "უშგული და შხარას ხედები",
        "en": "Ushguli & Mount Shkhara Views",
        "ru": "Ушгули и виды на Шхару",
        "ar": "أوشغولي وإطلالات جبل شخارا"
      },
      "description": {
        "ka": "უშგულის ისტორიული სოფელი და კავკასიონის მაღალი მწვერვალების ხედები.",
        "en": "Ushguli & Mount Shkhara Views. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Ушгули и виды на Шхару. Знакомство с местными достопримечательностями и природой.",
        "ar": "أوشغولي وإطلالات جبل شخارا. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "svaneti",
      "image": "/uploads/geojoy_tours_30.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo10",
      "name": {
        "ka": "ამბროლაური და შაორის წყალსაცავი",
        "en": "Ambrolauri & Shaori Reservoir",
        "ru": "Амбролаури и водохранилище Шаори",
        "ar": "أمبروولاوري وخزان شاوري"
      },
      "description": {
        "ka": "რაჭის ბუნება, შაორის წყალსაცავი და მთის სოფლები.",
        "en": "Ambrolauri & Shaori Reservoir. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Амбролаури и водохранилище Шаори. Знакомство с местными достопримечательностями и природой.",
        "ar": "أمبروولاوري وخزان شاوري. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "racha",
      "image": "/uploads/geojoy_tours_31.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo11",
      "name": {
        "ka": "ნიკორწმინდა და რაჭის სოფლები",
        "en": "Nikortsminda & Racha Villages",
        "ru": "Никорцминда и деревни Рачи",
        "ar": "نيكورتسميندا وقرى راتشا"
      },
      "description": {
        "ka": "ნიკორწმინდის ტაძარი და რაჭის ტრადიციული სოფლები.",
        "en": "Nikortsminda & Racha Villages. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Никорцминда и деревни Рачи. Знакомство с местными достопримечательностями и природой.",
        "ar": "نيكورتسميندا وقرى راتشا. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "racha",
      "image": "/uploads/geojoy_tours_32.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo12",
      "name": {
        "ka": "მცხეთა, ჯვარი და სვეტიცხოველი",
        "en": "Mtskheta, Jvari & Svetitskhoveli",
        "ru": "Мцхета, Джвари и Светицховели",
        "ar": "متسخيتا وجفاري وسفيتيتسخوفيلي"
      },
      "description": {
        "ka": "მცხეთის ისტორიული ცენტრი, ჯვრის მონასტერი და სვეტიცხოველი.",
        "en": "Mtskheta, Jvari & Svetitskhoveli. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Мцхета, Джвари и Светицховели. Знакомство с местными достопримечательностями и природой.",
        "ar": "متسخيتا وجفاري وسفيتيتسخوفيلي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "mtskheta",
      "image": "/uploads/geojoy_tours_33.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo13",
      "name": {
        "ka": "ყაზბეგი და გერგეტის სამება",
        "en": "Kazbegi & Gergeti Trinity",
        "ru": "Казбеги и Гергетская Троица",
        "ar": "كازبيغي وكنيسة غيرغيتي"
      },
      "description": {
        "ka": "საქართველოს სამხედრო გზა, სტეფანწმინდა და გერგეტის სამების ეკლესია.",
        "en": "Kazbegi & Gergeti Trinity. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Казбеги и Гергетская Троица. Знакомство с местными достопримечательностями и природой.",
        "ar": "كازبيغي وكنيسة غيرغيتي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "mtskheta",
      "image": "/uploads/geojoy_tours_34.webp",
      "imagePosition": "56% 50%"
    },
    {
      "id": "geo14",
      "name": {
        "ka": "გუდაური და ჯვრის უღელტეხილი",
        "en": "Gudauri & Jvari Pass",
        "ru": "Гудаури и Крестовый перевал",
        "ar": "غوداوري وممر جفاري"
      },
      "description": {
        "ka": "გუდაურის სამთო კურორტი და ჯვრის უღელტეხილის ხედები.",
        "en": "Gudauri & Jvari Pass. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Гудаури и Крестовый перевал. Знакомство с местными достопримечательностями и природой.",
        "ar": "غوداوري وممر جفاري. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "mtskheta",
      "image": "/uploads/geojoy_tours_35.webp",
      "imagePosition": "50% 48%"
    },
    {
      "id": "geo15",
      "name": {
        "ka": "ბორჯომი და ბორჯომ-ხარაგაულის ბუნება",
        "en": "Borjomi & National Park",
        "ru": "Боржоми и национальный парк",
        "ar": "بورجومي والحديقة الوطنية"
      },
      "description": {
        "ka": "ბორჯომის პარკი, მინერალური წყლები და მიმდებარე ბუნება.",
        "en": "Borjomi & National Park. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Боржоми и национальный парк. Знакомство с местными достопримечательностями и природой.",
        "ar": "بورجومي والحديقة الوطنية. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "samtskhe",
      "image": "/uploads/geojoy_tours_36.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo16",
      "name": {
        "ka": "ბაკურიანი — ოთხივე სეზონის კურორტი",
        "en": "Bakuriani Mountain Resort",
        "ru": "Горный курорт Бакуриани",
        "ar": "منتجع باكورياني الجبلي"
      },
      "description": {
        "ka": "ბაკურიანის სამთო კურორტი; სეზონის მიხედვით ზამთრისა თუ ზაფხულის აქტივობები.",
        "en": "Bakuriani Mountain Resort. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Горный курорт Бакуриани. Знакомство с местными достопримечательностями и природой.",
        "ar": "منتجع باكورياني الجبلي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "samtskhe",
      "image": "/uploads/geojoy_tours_37.webp",
      "imagePosition": "50% 45%"
    },
    {
      "id": "geo17",
      "name": {
        "ka": "ვარძია — კლდეში ნაკვეთი ქალაქი",
        "en": "Vardzia Cave City",
        "ru": "Пещерный город Вардзия",
        "ar": "مدينة فاردزيا المنحوتة في الصخر"
      },
      "description": {
        "ka": "შუა საუკუნეების კლდეში ნაკვეთი სამონასტრო კომპლექსი და მისი ისტორია.",
        "en": "Discover the medieval cave monastery complex and its history.",
        "ru": "Средневековый пещерный монастырский комплекс и его история.",
        "ar": "اكتشف مجمع الدير المنحوت في الصخر من العصور الوسطى وتاريخه."
      },
      "region": "samtskhe",
      "image": "/uploads/geojoy_tours_38.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo18",
      "name": {
        "ka": "სიღნაღი და ბოდბე",
        "en": "Sighnaghi & Bodbe",
        "ru": "Сигнахи и Бодбе",
        "ar": "سيغناغي وبودبي"
      },
      "description": {
        "ka": "სიღნაღის ისტორიული ქუჩები და ბოდბის მონასტერი.",
        "en": "Sighnaghi & Bodbe. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Сигнахи и Бодбе. Знакомство с местными достопримечательностями и природой.",
        "ar": "سيغناغي وبودبي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "kakheti",
      "image": "/uploads/geojoy_tours_39.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo19",
      "name": {
        "ka": "თელავი და ალავერდი",
        "en": "Telavi & Alaverdi",
        "ru": "Телави и Алаверди",
        "ar": "تيلافي وألاڤيردي"
      },
      "description": {
        "ka": "თელავის ისტორიული ადგილები და ალავერდის საკათედრო ტაძარი.",
        "en": "Telavi & Alaverdi. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Телави и Алаверди. Знакомство с местными достопримечательностями и природой.",
        "ar": "تيلافي وألاڤيردي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "kakheti",
      "image": "/uploads/geojoy_tours_40.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo20",
      "name": {
        "ka": "დავითგარეჯის სამონასტრო კომპლექსი",
        "en": "David Gareja Monastery",
        "ru": "Монастырский комплекс Давид-Гареджи",
        "ar": "مجمع دير دافيت غاريجا"
      },
      "description": {
        "ka": "ნახევრად უდაბნოს ლანდშაფტი და დავითგარეჯის კლდეში ნაკვეთი მონასტრები.",
        "en": "David Gareja Monastery. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Монастырский комплекс Давид-Гареджи. Знакомство с местными достопримечательностями и природой.",
        "ar": "مجمع دير دافيت غاريجا. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "kakheti",
      "image": "/uploads/geojoy_tours_41.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo21",
      "name": {
        "ka": "ქუთაისი, ბაგრატი და გელათი",
        "en": "Kutaisi, Bagrati & Gelati",
        "ru": "Кутаиси, Баграти и Гелати",
        "ar": "كوتايسي وباغراتي وجيلاتي"
      },
      "description": {
        "ka": "ქუთაისის ისტორიული ღირსშესანიშნაობები და გელათის მონასტერი.",
        "en": "Kutaisi, Bagrati & Gelati. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Кутаиси, Баграти и Гелати. Знакомство с местными достопримечательностями и природой.",
        "ar": "كوتايسي وباغراتي وجيلاتي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "imereti",
      "image": "/uploads/geojoy_tours_42.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo22",
      "name": {
        "ka": "პრომეთეს მღვიმე და სათაფლია",
        "en": "Prometheus Cave & Sataplia",
        "ru": "Пещера Прометея и Сатаплия",
        "ar": "كهف بروميثيوس وساتابليا"
      },
      "description": {
        "ka": "კარსტული მღვიმეები და სათაფლიას ბუნებრივი ტერიტორია.",
        "en": "Prometheus Cave & Sataplia. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Пещера Прометея и Сатаплия. Знакомство с местными достопримечательностями и природой.",
        "ar": "كهف بروميثيوس وساتابليا. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "imereti",
      "image": "/uploads/geojoy_tours_43.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo23",
      "name": {
        "ka": "დაშბაშის კანიონი და ბრილიანტის ხიდი",
        "en": "Dashbashi Canyon & Diamond Bridge",
        "ru": "Каньон Дашбаши и Алмазный мост",
        "ar": "وادي داشباشي والجسر الماسي"
      },
      "description": {
        "ka": "წალკის კანიონის ხედები და ბრილიანტის ხიდი.",
        "en": "Dashbashi Canyon & Diamond Bridge. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Каньон Дашбаши и Алмазный мост. Знакомство с местными достопримечательностями и природой.",
        "ar": "وادي داشباشي والجسر الماسي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "kvemo",
      "image": "/uploads/geojoy_tours_44.webp",
      "imagePosition": "50% 48%"
    },
    {
      "id": "geo24",
      "name": {
        "ka": "ბოლნისის ისტორიული მემკვიდრეობა",
        "en": "Bolnisi Heritage Tour",
        "ru": "Историческое наследие Болниси",
        "ar": "جولة تراث بولنيسي"
      },
      "description": {
        "ka": "ბოლნისის ისტორიული ძეგლები და რეგიონის კულტურული მემკვიდრეობა.",
        "en": "Bolnisi Heritage Tour. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Историческое наследие Болниси. Знакомство с местными достопримечательностями и природой.",
        "ar": "جولة تراث بولنيسي. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "kvemo",
      "image": "/uploads/geojoy_tours_45.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo25",
      "name": {
        "ka": "უფლისციხე და გორი",
        "en": "Uplistsikhe & Gori",
        "ru": "Уплисцихе и Гори",
        "ar": "أوبليستسيخي وغوري"
      },
      "description": {
        "ka": "კლდეში ნაკვეთი უძველესი ქალაქი უფლისციხე და გორის ისტორიული ადგილები.",
        "en": "Uplistsikhe & Gori. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Уплисцихе и Гори. Знакомство с местными достопримечательностями и природой.",
        "ar": "أوبليستسيخي وغوري. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "shida",
      "image": "/uploads/geojoy_tours_46.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo26",
      "name": {
        "ka": "ატენის სიონი და ტანის ხეობა",
        "en": "Ateni Sioni & Tana Valley",
        "ru": "Атенский Сиони и долина Тана",
        "ar": "أتيني سيوني ووادي تانا"
      },
      "description": {
        "ka": "ატენის სიონის ტაძარი და ტანის ხეობის ბუნება.",
        "en": "Ateni Sioni & Tana Valley. Explore local landmarks and landscapes with a private inquiry-based tour.",
        "ru": "Атенский Сиони и долина Тана. Знакомство с местными достопримечательностями и природой.",
        "ar": "أتيني سيوني ووادي تانا. اكتشف المعالم المحلية والطبيعة في جولة خاصة."
      },
      "region": "shida",
      "image": "/uploads/geojoy_tours_47.webp",
      "imagePosition": "50% 50%"
    },
    {
      "id": "geo28",
      "name": {
        "ka": "რაბათის ციხე ახალციხეში",
        "en": "Rabati Fortress in Akhaltsikhe",
        "ru": "Крепость Рабат в Ахалцихе",
        "ar": "قلعة الرباط في أخالتسيخه"
      },
      "description": {
        "ka": "ახალციხის ისტორიული ციხე-კომპლექსი და მისი არქიტექტურა.",
        "en": "Explore Akhaltsikhe’s historic fortress complex and architecture.",
        "ru": "Исторический крепостной комплекс Ахалцихе и его архитектура.",
        "ar": "اكتشف مجمع قلعة أخالتسيخه التاريخي وعمارتها."
      },
      "region": "samtskhe",
      "image": "/uploads/geojoy_tours_48.webp",
      "imagePosition": "52% 48%"
    },
    {
      "id": "geo29",
      "name": {
        "ka": "ჯვრის მონასტერი მცხეთაში",
        "en": "Jvari Monastery in Mtskheta",
        "ru": "Монастырь Джвари в Мцхете",
        "ar": "دير جفاري في متسخيتا"
      },
      "description": {
        "ka": "VI საუკუნის ჯვრის მონასტერი და მტკვრისა და არაგვის შესართავის ხედები.",
        "en": "Visit the sixth-century Jvari Monastery overlooking the Aragvi and Mtkvari rivers.",
        "ru": "Монастырь Джвари VI века с видом на слияние рек Арагви и Куры.",
        "ar": "زر دير جفاري من القرن السادس المطل على ملتقى نهري أراغفي ومتكواري."
      },
      "region": "mtskheta",
      "image": "/uploads/geojoy_tours_49.webp",
      "imagePosition": "50% 50%"
    }
  ],
  "transfers": [
    {
      "id": "tr1",
      "icon": "✈",
      "name": {
        "ka": "აეროპორტის ტრანსფერი",
        "en": "Airport transfer",
        "ru": "Трансфер из аэропорта",
        "ar": "النقل من المطار"
      },
      "description": {
        "ka": "დაგხვედრა და კომფორტული მგზავრობა დანიშნულების ადგილამდე.",
        "en": "A convenient pickup and comfortable ride to your destination.",
        "ru": "Удобная встреча и комфортная поездка до места назначения.",
        "ar": "استقبال مريح ورحلة إلى وجهتك."
      },
      "image": "/uploads/geojoy_transfers_50.webp"
    },
    {
      "id": "tr2",
      "icon": "↗",
      "name": {
        "ka": "ქალაქებს შორის",
        "en": "Intercity transfer",
        "ru": "Междугородний трансфер",
        "ar": "النقل بين المدن"
      },
      "description": {
        "ka": "მოსახერხებელი გადაადგილება საქართველოს ქალაქებს შორის.",
        "en": "Comfortable travel between cities in Georgia.",
        "ru": "Комфортные поездки между городами Грузии.",
        "ar": "تنقل مريح بين مدن جورجيا."
      },
      "image": "/uploads/geojoy_transfers_51.webp"
    },
    {
      "id": "tr3",
      "icon": "🚘",
      "name": {
        "ka": "კერძო ტრანსფერი",
        "en": "Private transfer",
        "ru": "Индивидуальный трансфер",
        "ar": "نقل خاص"
      },
      "description": {
        "ka": "მარშრუტი და დრო შენს საჭიროებებზე მორგებით.",
        "en": "A route and schedule tailored to your needs.",
        "ru": "Маршрут и время под ваши потребности.",
        "ar": "مسار ووقت يناسبان احتياجاتك."
      },
      "image": "/uploads/geojoy_transfers_52.webp"
    },
    {
      "id": "tr4",
      "icon": "⌂",
      "name": {
        "ka": "სასტუმროს ტრანსფერი",
        "en": "Hotel transfer",
        "ru": "Трансфер в отель",
        "ar": "النقل إلى الفندق"
      },
      "description": {
        "ka": "მარტივი გადაადგილება სასტუმრომდე ან სასტუმროდან.",
        "en": "Easy transportation to or from your hotel.",
        "ru": "Удобная поездка в отель или из отеля.",
        "ar": "تنقل سهل من الفندق وإليه."
      },
      "image": "/uploads/geojoy_transfers_53.webp"
    },
    {
      "id": "tr5",
      "icon": "▣",
      "name": {
        "ka": "7-ადგილიანი მინივენი",
        "en": "7-seat minivan",
        "ru": "Минивэн на 7 мест",
        "ar": "حافلة صغيرة لسبعة مقاعد"
      },
      "description": {
        "ka": "მოსახერხებელი მგზავრობა ოჯახისა და მცირე ჯგუფისთვის.",
        "en": "Comfortable travel for families and small groups.",
        "ru": "Комфортные поездки для семей и небольших групп.",
        "ar": "تنقل مريح للعائلات والمجموعات الصغيرة."
      },
      "image": "/uploads/geojoy_transfers_54.webp"
    },
    {
      "id": "tr6",
      "icon": "✦",
      "name": {
        "ka": "სხვა მარშრუტი",
        "en": "Custom route",
        "ru": "Индивидуальный маршрут",
        "ar": "مسار مخصص"
      },
      "description": {
        "ka": "მოგვწერე სასურველი მარშრუტი და დეტალები.",
        "en": "Tell us your preferred route and details.",
        "ru": "Расскажите о желаемом маршруте и деталях.",
        "ar": "أخبرنا عن مسارك المفضل والتفاصيل."
      },
      "image": "/uploads/geojoy_transfers_55.webp"
    }
  ],
  "contact": {
    "telegram": "",
    "whatsapp": "",
    "phone": "",
    "email": ""
  },
  "siteVersion": "8.9.0",
  "about": {
    "image": "/uploads/geojoy_about_60.webp",
    "eyebrow": {
      "ka": "ჩვენ შესახებ",
      "en": "ABOUT GEOJOY",
      "ru": "О GEOJOY",
      "ar": "عن GEOJOY"
    },
    "title": {
      "ka": "საქართველო — გულით აღმოსაჩენი",
      "en": "Georgia, made to be discovered",
      "ru": "Грузия, которую хочется открывать",
      "ar": "جورجيا تستحق أن تكتشفها"
    },
    "lead": {
      "ka": "GeoJoy შეიქმნა იმისთვის, რომ საქართველოს გაცნობა უფრო მარტივი, გასაგები და შენს ინტერესებზე მორგებული იყოს.",
      "en": "GeoJoy is designed to make discovering Georgia simpler, clearer, and better suited to your interests.",
      "ru": "GeoJoy помогает знакомиться с Грузией проще, понятнее и с учётом ваших интересов.",
      "ar": "تساعدك GeoJoy على اكتشاف جورجيا بطريقة أسهل وأوضح تتناسب مع اهتماماتك."
    },
    "body": {
      "ka": "ჩვენ ერთ სივრცეში ვაერთიანებთ ქვეყნის გამორჩეულ ადგილებს, ტურების იდეებსა და ტრანსფერის მოთხოვნას. გვსურს, დაგეხმაროთ ისეთი მარშრუტის შერჩევაში, რომელიც შენს დროს, ინტერესებსა და მოგზაურობის სტილს შეესაბამება.",
      "en": "We bring together remarkable places, tour ideas, and transfer requests in one place. Our goal is to help you choose a route that fits your time, interests, and travel style.",
      "ru": "Мы объединяем интересные места страны, идеи экскурсий и запросы на трансфер в одном пространстве. Наша цель — помочь подобрать маршрут с учётом вашего времени, интересов и стиля путешествия.",
      "ar": "نجمع أبرز الأماكن وأفكار الجولات وطلبات النقل في مكان واحد، لمساعدتك في اختيار مسار يناسب وقتك واهتماماتك وأسلوب سفرك."
    },
    "point1Title": {
      "ka": "მარშრუტი შენს ინტერესებზე",
      "en": "Routes shaped around you",
      "ru": "Маршрут под ваши интересы",
      "ar": "مسار يناسب اهتماماتك"
    },
    "point1Body": {
      "ka": "ქალაქი, მთები, ბუნება თუ კულტურა — შეარჩიე მიმართულება და მოგვწერე სურვილები.",
      "en": "Cities, mountains, nature, or culture — choose a direction and tell us what matters to you.",
      "ru": "Город, горы, природа или культура — выберите направление и расскажите о пожеланиях.",
      "ar": "المدن أو الجبال أو الطبيعة أو الثقافة — اختر وجهتك وأخبرنا بما تفضله."
    },
    "point2Title": {
      "ka": "დეტალები წინასწარ შეთანხმებით",
      "en": "Details agreed in advance",
      "ru": "Детали согласуются заранее",
      "ar": "الاتفاق على التفاصيل مسبقاً"
    },
    "point2Body": {
      "ka": "თარიღს, მგზავრების რაოდენობას, მარშრუტსა და სხვა პირობებს შეკვეთამდე ვაზუსტებთ.",
      "en": "We clarify the date, group size, route, and key details before confirming a request.",
      "ru": "До подтверждения уточняются дата, количество путешественников, маршрут и важные условия.",
      "ar": "نوضح التاريخ وعدد المسافرين والمسار والتفاصيل المهمة قبل تأكيد الطلب."
    },
    "point3Title": {
      "ka": "პირდაპირი კომუნიკაცია",
      "en": "Direct communication",
      "ru": "Прямая связь",
      "ar": "تواصل مباشر"
    },
    "point3Body": {
      "ka": "გამოიყენე საკონტაქტო არხები ან მოთხოვნის ფორმა, რომ დაგეგმვა კონკრეტული დეტალებით დავიწყოთ.",
      "en": "Use the contact channels or request form so planning can begin with the right details.",
      "ru": "Используйте контактные каналы или форму запроса, чтобы начать планирование с конкретных деталей.",
      "ar": "استخدم قنوات التواصل أو نموذج الطلب لبدء التخطيط بتفاصيل واضحة."
    },
    "cta": {
      "ka": "დაგეგმვა დაიწყე",
      "en": "Start planning",
      "ru": "Начать планирование",
      "ar": "ابدأ التخطيط"
    },
    "imagePosition": "center 50%"
  },
  "siteTexts": {
    "navTours": {
      "ka": "ტურები",
      "en": "Tours",
      "ru": "Туры",
      "ar": "الجولات"
    },
    "navTransfers": {
      "ka": "ტრანსფერები",
      "en": "Transfers",
      "ru": "Трансферы",
      "ar": "التنقلات"
    },
    "navRegions": {
      "ka": "რეგიონები",
      "en": "Regions",
      "ru": "Регионы",
      "ar": "المناطق"
    },
    "navContact": {
      "ka": "კონტაქტი",
      "en": "Contact",
      "ru": "Контакты",
      "ar": "اتصل بنا"
    },
    "heroEyebrow": {
      "ka": "აღმოაჩინე საქართველო GeoJoy-თან ერთად",
      "en": "Discover Georgia with GeoJoy",
      "ru": "Откройте Грузию с GeoJoy",
      "ar": "اكتشف جورجيا مع GeoJoy"
    },
    "heroBottom": {
      "ka": "შენი მოგზაურობა იწყება აქ",
      "en": "Your journey starts here",
      "ru": "Ваше путешествие начинается здесь",
      "ar": "رحلتك تبدأ هنا"
    },
    "featuredLabel": {
      "ka": "შერჩეული გამოცდილებები",
      "en": "Selected experiences",
      "ru": "Подобранные впечатления",
      "ar": "تجارب مختارة"
    },
    "toursTitle": {
      "ka": "ტურები",
      "en": "Tours",
      "ru": "Туры",
      "ar": "الجولات"
    },
    "toursSubtitle": {
      "ka": "აღმოაჩინე საქართველოს გამორჩეული ადგილები.",
      "en": "Discover the remarkable places of Georgia.",
      "ru": "Откройте для себя удивительные места Грузии.",
      "ar": "اكتشف الأماكن المميزة في جورجيا."
    },
    "viewAll": {
      "ka": "ყველა ტური",
      "en": "All tours",
      "ru": "Все туры",
      "ar": "كل الجولات"
    },
    "comfortLabel": {
      "ka": "მარტივად და კომფორტულად",
      "en": "Easy and comfortable",
      "ru": "Легко и комфортно",
      "ar": "بسهولة وراحة"
    },
    "transfersTitle": {
      "ka": "ტრანსფერები",
      "en": "Transfers",
      "ru": "Трансферы",
      "ar": "التنقلات"
    },
    "transfersSubtitle": {
      "ka": "სანდო გადაადგილება შენს მარშრუტზე.",
      "en": "Reliable transportation for your journey.",
      "ru": "Надёжная поездка по вашему маршруту.",
      "ar": "تنقل موثوق يناسب رحلتك."
    },
    "viewServices": {
      "ka": "ყველა სერვისი",
      "en": "All services",
      "ru": "Все услуги",
      "ar": "كل الخدمات"
    },
    "discoverLabel": {
      "ka": "აღმოაჩინე საქართველო",
      "en": "Discover Georgia",
      "ru": "Откройте Грузию",
      "ar": "اكتشف جورجيا"
    },
    "regionsTitle": {
      "ka": "საქართველოს რეგიონები",
      "en": "Regions of Georgia",
      "ru": "Регионы Грузии",
      "ar": "مناطق جورجيا"
    },
    "regionsSubtitle": {
      "ka": "თითოეულ კუთხეს თავისი ხასიათი და ისტორია აქვს.",
      "en": "Every corner has its own character and story.",
      "ru": "У каждого края свой характер и история.",
      "ar": "لكل منطقة طابعها وقصتها الخاصة."
    },
    "viewAllRegions": {
      "ka": "ყველა რეგიონი",
      "en": "All regions",
      "ru": "Все регионы",
      "ar": "كل المناطق"
    },
    "contactEyebrow": {
      "ka": "დავგეგმოთ შენი მოგზაურობა",
      "en": "Let’s plan your journey",
      "ru": "Спланируем путешествие",
      "ar": "لنخطط رحلتك"
    },
    "contactTitle": {
      "ka": "გაქვს შეკითხვა ან გეგმა?",
      "en": "Have a question or a plan?",
      "ru": "Есть вопрос или план?",
      "ar": "هل لديك سؤال أو خطة؟"
    },
    "contactSubtitle": {
      "ka": "მოგვწერე და ერთად ვიპოვოთ შენთვის საუკეთესო გზა.",
      "en": "Tell us what you have in mind and we’ll help you find the right way.",
      "ru": "Напишите нам, и мы поможем подобрать подходящий вариант.",
      "ar": "راسلنا وسنساعدك في اختيار الأنسب."
    },
    "sendRequest": {
      "ka": "მოთხოვნის გაგზავნა ↗",
      "en": "Send an inquiry ↗",
      "ru": "Отправить запрос ↗",
      "ar": "إرسال طلب ↗"
    },
    "footerText": {
      "ka": "საქართველო, შენი ტემპით.",
      "en": "Georgia, at your own pace.",
      "ru": "Грузия в вашем ритме.",
      "ar": "جورجيا على إيقاعك."
    },
    "telegram": {
      "ka": "Telegram",
      "en": "Telegram",
      "ru": "Telegram",
      "ar": "Telegram"
    },
    "requestTitle": {
      "ka": "მოგვწერე შენი გეგმა",
      "en": "Tell us about your plans",
      "ru": "Расскажите о планах",
      "ar": "أخبرنا عن خطتك"
    },
    "fieldKind": {
      "ka": "მოთხოვნის ტიპი",
      "en": "Request type",
      "ru": "Тип запроса",
      "ar": "نوع الطلب"
    },
    "fieldService": {
      "ka": "სერვისი / მარშრუტი",
      "en": "Service / route",
      "ru": "Услуга / маршрут",
      "ar": "الخدمة / المسار"
    },
    "fieldDate": {
      "ka": "თარიღი",
      "en": "Date",
      "ru": "Дата",
      "ar": "التاريخ"
    },
    "fieldPeople": {
      "ka": "მგზავრები",
      "en": "Passengers",
      "ru": "Пассажиры",
      "ar": "عدد المسافرين"
    },
    "fieldName": {
      "ka": "სახელი",
      "en": "Name",
      "ru": "Имя",
      "ar": "الاسم"
    },
    "fieldContact": {
      "ka": "ტელეფონი",
      "en": "Phone",
      "ru": "Телефон",
      "ar": "الهاتف"
    },
    "fieldPickup": {
      "ka": "საიდან",
      "en": "Pickup",
      "ru": "Откуда",
      "ar": "من أين"
    },
    "fieldDestination": {
      "ka": "სად",
      "en": "Destination",
      "ru": "Куда",
      "ar": "إلى أين"
    },
    "fieldNote": {
      "ka": "შეტყობინება (არასავალდებულო)",
      "en": "Message (optional)",
      "ru": "Сообщение (необязательно)",
      "ar": "رسالة (اختياري)"
    },
    "tour": {
      "ka": "ტური",
      "en": "Tour",
      "ru": "Тур",
      "ar": "جولة"
    },
    "transfer": {
      "ka": "ტრანსფერი",
      "en": "Transfer",
      "ru": "Трансфер",
      "ar": "تنقل"
    },
    "details": {
      "ka": "დეტალები ↗",
      "en": "Details ↗",
      "ru": "Подробнее ↗",
      "ar": "التفاصيل ↗"
    },
    "request": {
      "ka": "მოთხოვნა ↗",
      "en": "Request ↗",
      "ru": "Запрос ↗",
      "ar": "طلب ↗"
    },
    "language": {
      "ka": "ენა",
      "en": "Language",
      "ru": "Язык",
      "ar": "اللغة"
    },
    "filterByRegion": {
      "ka": "არჩეული რეგიონი",
      "en": "Selected region",
      "ru": "Выбранный регион",
      "ar": "المنطقة المحددة"
    },
    "clearFilter": {
      "ka": "ყველა ტურის ნახვა",
      "en": "Show all tours",
      "ru": "Показать все туры",
      "ar": "عرض كل الجولات"
    },
    "noTours": {
      "ka": "ამ რეგიონში ტური ჯერ დამატებული არ არის",
      "en": "No tours have been added for this region yet",
      "ru": "Для этого региона туры пока не добавлены",
      "ar": "لم تتم إضافة جولات لهذه المنطقة بعد"
    },
    "tourCount": {
      "ka": "ტური",
      "en": "tours",
      "ru": "тур(ов)",
      "ar": "جولات"
    },
    "viewTours": {
      "ka": "ამ რეგიონის ტურები",
      "en": "View regional tours",
      "ru": "Туры региона",
      "ar": "جولات المنطقة"
    },
    "navAbout": {
      "ka": "ჩვენ შესახებ",
      "en": "About us",
      "ru": "О нас",
      "ar": "من نحن"
    },
    "transferPhotoKicker": {
      "ka": "GEOJOY · პირადი ტრანსფერები",
      "en": "GEOJOY · PRIVATE TRANSFERS",
      "ru": "GEOJOY · ЧАСТНЫЕ ТРАНСФЕРЫ",
      "ar": "GEOJOY · نقل خاص"
    },
    "transferPhotoTitle": {
      "ka": "კომფორტული გზა იწყება აქ",
      "en": "Comfort starts with the journey",
      "ru": "Комфорт начинается с дороги",
      "ar": "تبدأ الراحة من الطريق"
    },
    "transferPhotoSubtitle": {
      "ka": "პირადი ტრანსფერი • ფართო მინივენი • შენი მარშრუტი",
      "en": "Private transfer • spacious minivan • your route",
      "ru": "Индивидуальный трансфер • просторный минивэн • ваш маршрут",
      "ar": "نقل خاص • حافلة صغيرة واسعة • مسارك"
    }
  },
  "transferSettings": {
    "image": "/uploads/geojoy_transferslides_56.webp",
    "imagePosition": "50% 48%",
    "slides": [
      {
        "id": "vehicle-minivan",
        "image": "/uploads/geojoy_transferslides_56.webp",
        "imagePosition": "50% 48%",
        "label": {
          "ka": "კომფორტული მინივენი",
          "en": "Comfortable minivan",
          "ru": "Комфортабельный минивэн",
          "ar": "ميني فان مريح"
        }
      },
      {
        "id": "vehicle-sprinter",
        "image": "/uploads/geojoy_transferslides_57.webp",
        "imagePosition": "50% 48%",
        "label": {
          "ka": "Mercedes-Benz Sprinter — მიკროავტობუსი",
          "en": "Mercedes-Benz Sprinter minibus",
          "ru": "Микроавтобус Mercedes-Benz Sprinter",
          "ar": "حافلة صغيرة مرسيدس-بنز سبرينتر"
        }
      },
      {
        "id": "vehicle-delica-4x4",
        "image": "/uploads/geojoy_transferslides_58.webp",
        "imagePosition": "50% 48%",
        "label": {
          "ka": "Mitsubishi Delica 4×4 — ყველგანმავალი",
          "en": "Mitsubishi Delica 4×4 off-road van",
          "ru": "Mitsubishi Delica 4×4 — внедорожный минивэн",
          "ar": "ميتسوبيشي ديليكا 4×4 للطرق الوعرة"
        }
      },
      {
        "id": "vehicle-sedan",
        "image": "/uploads/geojoy_transferslides_59.webp",
        "imagePosition": "50% 50%",
        "label": {
          "ka": "პრემიუმ სედანი",
          "en": "Premium sedan",
          "ru": "Премиальный седан",
          "ar": "سيارة سيدان فاخرة"
        }
      }
    ]
  }
}''')

LEGACY_IMAGE_URLS = {'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=900&q=80', 'https://commons.wikimedia.org/wiki/Special:FilePath/Bagrati_Cathedral.jpg?width=1200', 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=900&q=80', 'https://commons.wikimedia.org/wiki/Special:FilePath/2015-08-27_(28)_Shaori_reservoir.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Bagrati_Cathedral.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Georgian_Woman_in_a_Tea_Farm.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Seaside_of_Batumi.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Borjomi_Park.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Bolnisis_sioni.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Gergeti_Trinity_Church,_Kazbegi.jpg?width=1400', 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=900&q=80', 'https://commons.wikimedia.org/wiki/Special:FilePath/Gudauri_ski_resort,_Georgia_01.jpg?width=1100', 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=900&q=80', 'https://commons.wikimedia.org/wiki/Special:FilePath/Nikortsminda_Cathedral.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Georgian_Woman_in_a_Tea_Farm.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Panoramic_view_of_Old_Tbilisi.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Svetitskhoveli_Cathedral,_Mtskheta.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Towers_of_Svaneti.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Uplistsikhe.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Dashbashi_canyon.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Gergeti_Trinity_Church,_Kazbegi.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Makhuntseti_waterfall.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Ushguli_Village,_Svaneti,_view_of_Shkhara_mountain.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Martvili_Canyon.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Towers_of_Svaneti.jpg?width=1200', 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80', 'https://commons.wikimedia.org/wiki/Special:FilePath/Atenis_Sioni.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Martvili_Canyon.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Vardzia,_Georgia.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Towers_of_Svaneti.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Bakuriani_Ski_Resort_(GEO)_2019.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Vardzia,_Georgia.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Alaverdi_Monastery_in_Kakheti,_Georgia.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Panoramic_view_of_Old_Tbilisi.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Nikortsminda_Cathedral.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Dashbashi_canyon.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Dashbashi_canyon.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Akhaltsikhe_(Rabati)_Castle.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Jvari_Monastery_Mtskheta.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Vardzia,_Georgia.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Okatse_canyon.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Gudauri_ski_resort,_Georgia_01.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Panoramic_view_of_Old_Tbilisi.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Seaside_of_Batumi.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Sighnaghi,_Georgia.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Borjomi_Park.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Seaside_of_Batumi.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Prometheus_cave,_Georgia.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/David_Gareja_Monastery,_Georgia.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Martvili_Canyon.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Svetitskhoveli_Cathedral,_Mtskheta.jpg?width=1100', 'https://commons.wikimedia.org/wiki/Special:FilePath/Sighnaghi,_Georgia.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:FilePath/Sighnaghi,_Georgia.jpg?width=1400', 'https://commons.wikimedia.org/wiki/Special:FilePath/Uplistsikhe.jpg?width=1200'}

def _localized_key(obj):
    """Normalize region names across Georgian/English/Russian aliases (especially Tbilisi)."""
    name = obj.get('name', {}) if isinstance(obj, dict) else {}
    if isinstance(name, dict):
        values = [name.get(lang, '') for lang in ('ka', 'en', 'ru', 'ar')]
    else:
        values = [name]
    normalized = []
    for raw in values:
        value = re.sub(r'\s+', ' ', str(raw or '')).strip().casefold()
        if not value:
            continue
        compact = re.sub(r'[\s.,:;()_\-–—]+', '', value)
        compact = re.sub(r'^(ქალაქი|ქ)', '', compact)
        for suffix in ('რეგიონი', 'region', 'регион', 'منطقة'):
            if compact.endswith(suffix):
                compact = compact[:-len(suffix)]
        if compact.startswith('თბილის') or compact.startswith('tbilisi') or compact.startswith('тбилиси'):
            return 'tbilisi'
        if compact in {'تبليسي', 'تبليسى'}:
            return 'tbilisi'
        if compact.endswith('ის') and compact.startswith('თბილის'):
            compact = compact[:-2]
        normalized.append(compact)
    # Prefer Georgian where available, but fall back to another language for incomplete admin entries.
    return next((x for x in normalized if x), '')


def _normalise_transfer_settings(settings):
    """Upgrade legacy single-photo settings to an editable slideshow while preserving custom images."""
    if not isinstance(settings, dict):
        settings = json.loads(json.dumps(SEED['transferSettings'], ensure_ascii=False))
    defaults = SEED.get('transferSettings', {})
    supplied = settings.get('slides')
    if not isinstance(supplied, list):
        legacy_image = str(settings.get('image', '') or '').strip()
        legacy_pos = str(settings.get('imagePosition', '50% 50%') or '50% 50%')
        supplied = json.loads(json.dumps(defaults.get('slides', []), ensure_ascii=False))
        if supplied and legacy_image:
            supplied[0]['image'] = legacy_image
            supplied[0]['imagePosition'] = legacy_pos
    clean = []
    for idx, slide in enumerate(supplied):
        if not isinstance(slide, dict):
            continue
        item = dict(slide)
        item['id'] = str(item.get('id') or f'vehicle-slide-{idx+1}')[:120]
        item['image'] = str(item.get('image') or '').strip()
        item['imagePosition'] = str(item.get('imagePosition') or '50% 50%')[:80]
        label = item.get('label') if isinstance(item.get('label'), dict) else {}
        clean_label = {}
        for language in ('ka', 'en', 'ru', 'ar'):
            default_label = (defaults.get('slides', [{}])[min(idx, max(0, len(defaults.get('slides', []))-1))].get('label', {}) or {}).get(language, '') if defaults.get('slides') else ''
            clean_label[language] = str(label.get(language) or default_label or '')[:250]
        item['label'] = clean_label
        clean.append(item)
    settings['slides'] = clean
    # Keep the legacy fields synchronized for compatibility with any older admin code.
    first = next((x for x in clean if x.get('image')), None)
    settings['image'] = first['image'] if first else ''
    settings['imagePosition'] = first.get('imagePosition', '50% 50%') if first else '50% 50%'
    return settings

def _dedupe_region_catalog(data):
    """Remove duplicate regions on writes and redirect tours to the surviving region."""
    regions = data.get('regions', [])
    if not isinstance(regions, list):
        data['regions'] = []
        return data
    seed_by_id = {str(r.get('id')): r for r in SEED.get('regions', [])}
    seed_by_name = {_localized_key(r): str(r.get('id')) for r in SEED.get('regions', [])}
    keep, seen_ids, seen_names, redirects = [], {}, {}, {}
    for region in regions:
        if not isinstance(region, dict):
            continue
        old_id = str(region.get('id', '')).strip()
        name_key = _localized_key(region)
        canonical = old_id if old_id in seed_by_id else seed_by_name.get(name_key, old_id)
        canonical = canonical or old_id or ('custom-region-' + str(len(keep) + 1))
        if canonical in seen_ids:
            redirects[old_id] = seen_ids[canonical]
            continue
        if name_key and name_key in seen_names:
            redirects[old_id] = seen_names[name_key]
            continue
        if canonical in seed_by_id:
            region['id'] = canonical
            # Keep admin-edited names/descriptions and photos.
        else:
            region['id'] = canonical
        keep.append(region)
        seen_ids[canonical] = region['id']
        if name_key:
            seen_names[name_key] = region['id']
    for tour in data.get('tours', []) if isinstance(data.get('tours'), list) else []:
        if isinstance(tour, dict):
            rid = str(tour.get('region', ''))
            if rid in redirects:
                tour['region'] = redirects[rid]
    data['regions'] = keep
    return data

def _tour_region_key(tour, regions):
    """Return canonical region key for a tour, resolving known region IDs and aliases."""
    rid = str(tour.get('region', '') or '').strip()
    for region in regions if isinstance(regions, list) else []:
        if isinstance(region, dict) and str(region.get('id', '')).strip() == rid:
            return _localized_key(region)
    compact = re.sub(r'[\s.,:;()_\-–—]+', '', rid).casefold()
    if compact.startswith('თბილის') or compact.startswith('tbilisi') or compact.startswith('тбилиси') or compact in {'تبليسي','تبليسى'}:
        return 'tbilisi'
    for suffix in ('რეგიონი','region','регион'):
        if compact.endswith(suffix): compact = compact[:-len(suffix)]
    if compact.startswith('თბილის') or compact.startswith('tbilisi') or compact.startswith('тбилиси'):
        return 'tbilisi'
    return compact


def _dedupe_tour_catalog(data):
    """Keep one Tbilisi tour (prefer geo01) and remove duplicate tour IDs."""
    tours = data.get('tours', [])
    if not isinstance(tours, list):
        data['tours'] = []
        return data
    regions = data.get('regions', [])
    tb_candidates = [t for t in tours if isinstance(t, dict) and _tour_region_key(t, regions) == 'tbilisi']
    preferred = next((t for t in tb_candidates if str(t.get('id', '')) == 'geo01'), None)
    if preferred is None and tb_candidates:
        preferred = tb_candidates[0]
    preferred_id = str(preferred.get('id', '')) if preferred else None
    keep, seen_ids = [], set()
    kept_tbilisi = False
    for tour in tours:
        if not isinstance(tour, dict):
            continue
        tour_id = str(tour.get('id', '') or '').strip()
        if tour_id and tour_id in seen_ids:
            continue
        if tour_id:
            seen_ids.add(tour_id)
        if _tour_region_key(tour, regions) == 'tbilisi':
            if kept_tbilisi:
                continue
            # If geo01 exists, do not keep a duplicate listed before it.
            if preferred_id and tour_id != preferred_id:
                continue
            kept_tbilisi = True
        keep.append(tour)
    data['tours'] = keep
    return data


def _migrate_transfer_vehicle_slides(settings):
    """Add the two new vehicle slides once on version upgrade, while retaining custom slides."""
    settings = _normalise_transfer_settings(settings)
    slides = settings['slides']
    existing = {str(x.get('id', '')) for x in slides if isinstance(x, dict)}
    defaults = {str(x.get('id', '')): x for x in SEED.get('transferSettings', {}).get('slides', [])}
    canonical_order = [str(x.get('id', '')) for x in SEED.get('transferSettings', {}).get('slides', [])]
    for required_id in ('vehicle-sprinter', 'vehicle-delica-4x4'):
        if required_id in existing or required_id not in defaults:
            continue
        slide = json.loads(json.dumps(defaults[required_id], ensure_ascii=False))
        target_pos = canonical_order.index(required_id)
        # Insert after the nearest earlier canonical vehicle that already exists.
        insert_at = None
        for previous_id in reversed(canonical_order[:target_pos]):
            for index, item in enumerate(slides):
                if str(item.get('id', '')) == previous_id:
                    insert_at = index + 1
                    break
            if insert_at is not None:
                break
        # Otherwise insert before the next known canonical slide, or at the end.
        if insert_at is None:
            for next_id in canonical_order[target_pos + 1:]:
                for index, item in enumerate(slides):
                    if str(item.get('id', '')) == next_id:
                        insert_at = index
                        break
                if insert_at is not None:
                    break
        if insert_at is None:
            insert_at = len(slides)
        slides.insert(insert_at, slide)
        existing.add(required_id)
    first = next((x for x in slides if x.get('image')), None)
    settings['image'] = first['image'] if first else ''
    settings['imagePosition'] = first.get('imagePosition', '50% 50%') if first else '50% 50%'
    return settings


def _normalize_recovery_word(value):
    """Normalize a user-chosen recovery phrase without ever storing it in plain text."""
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


def _secret_hash(secret, salt_hex=None):
    salt_hex = salt_hex or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256', str(secret).encode('utf-8'), bytes.fromhex(salt_hex), PASSWORD_HASH_ITERATIONS
    ).hex()
    return salt_hex, digest


def _verify_secret(secret, salt_hex, expected_hash):
    if not salt_hex or not expected_hash:
        return False
    try:
        _, actual = _secret_hash(secret, salt_hex)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, str(expected_hash))


def _verify_admin_password(password, con=None):
    owns_connection = con is None
    con = con or connect_db()
    try:
        row = con.execute('SELECT password_salt,password_hash FROM admin_security WHERE id=1').fetchone()
        return bool(row and _verify_secret(password, row['password_salt'], row['password_hash']))
    finally:
        if owns_connection:
            con.close()


def _safe_compare_text(left, right):
    # compare_digest(str, str) accepts ASCII-only strings; compare UTF-8 bytes to support Georgian passwords/phrases.
    return hmac.compare_digest(str(left).encode('utf-8'), str(right).encode('utf-8'))


def _valid_new_password(password):
    return isinstance(password, str) and len(password) >= MIN_PASSWORD_LENGTH and len(password) <= 256


def connect_db():
    # Migrate saved v5/v4 content and uploaded images from a neighboring project folder without editing its database.
    if not DB_PATH.exists():
        # Prefer a database from a separately extracted older v8 folder if present, then fall back to v7/v6/v5/v4.
        sibling_v8_databases = sorted(
            (folder / 'geojoy_v8.db' for folder in ROOT.parent.glob('GeoJoyLuxury*')
             if folder.resolve() != ROOT.resolve() and (folder / 'geojoy_v8.db').exists()),
            key=lambda candidate: candidate.stat().st_mtime,
            reverse=True,
        )
        candidates = sibling_v8_databases + [ROOT.parent / 'geojoy_v8.db', ROOT.parent / 'GeoJoyLuxury_v7' / 'geojoy_v7.db', ROOT.parent / 'geojoy_v7.db', ROOT.parent / 'GeoJoyLuxury_v6' / 'geojoy_v6.db', ROOT.parent / 'geojoy_v6.db', ROOT.parent / 'GeoJoyLuxury_v5' / 'geojoy_v5.db', ROOT.parent / 'geojoy_v5.db', ROOT.parent / 'GeoJoyLuxury_v4' / 'geojoy_v4.db', ROOT.parent / 'geojoy_v4.db']
        legacy = next((candidate for candidate in candidates if candidate.exists()), None)
        if legacy:
            import shutil
            shutil.copy2(legacy, DB_PATH)
            old_uploads = legacy.parent / 'uploads'
            if old_uploads.exists():
                for upload in old_uploads.iterdir():
                    if upload.is_file() and upload.name != '.gitkeep':
                        (UPLOADS / upload.name).write_bytes(upload.read_bytes())
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY CHECK (id=1), json TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, kind TEXT, service TEXT, date TEXT, pickup TEXT, destination TEXT, people TEXT, name TEXT, contact TEXT, note TEXT, status TEXT DEFAULT "New")')
    con.execute('''CREATE TABLE IF NOT EXISTS admin_security (
        id INTEGER PRIMARY KEY CHECK (id=1),
        password_salt TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        recovery_salt TEXT,
        recovery_hash TEXT,
        password_updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        recovery_updated_at TEXT
    )''')
    security_row = con.execute('SELECT id FROM admin_security WHERE id=1').fetchone()
    if security_row is None:
        password_salt, password_hash = _secret_hash(ADMIN_PASSWORD)
        con.execute(
            'INSERT INTO admin_security (id,password_salt,password_hash,recovery_salt,recovery_hash) VALUES (1,?,?,NULL,NULL)',
            (password_salt, password_hash)
        )
        con.commit()
    row = con.execute('SELECT json FROM content WHERE id=1').fetchone()
    if row is None:
        initial = json.loads(json.dumps(SEED, ensure_ascii=False))
        initial['siteVersion'] = APP_VERSION
        con.execute('INSERT INTO content (id,json) VALUES (1,?)', (json.dumps(initial, ensure_ascii=False),))
        con.commit()
        return con
    try:
        current = json.loads(row['json'])
        if not isinstance(current, dict): raise ValueError('bad content structure')
        previous_site_version = str(current.get('siteVersion', '') or '')
        changed = False
        if not isinstance(current.get('brand'), dict):
            current['brand'] = json.loads(json.dumps(SEED['brand'], ensure_ascii=False)); changed = True
        else:
            for key, value in SEED['brand'].items():
                if key not in current['brand']:
                    current['brand'][key] = value; changed = True
        if not isinstance(current.get('about'), dict):
            current['about'] = json.loads(json.dumps(SEED['about'], ensure_ascii=False)); changed = True
        else:
            # Add newly manageable about fields without overwriting text that the owner edited.
            for key, value in SEED['about'].items():
                if key not in current['about']:
                    current['about'][key] = value; changed = True
        if not isinstance(current.get('siteTexts'), dict):
            current['siteTexts'] = json.loads(json.dumps(SEED['siteTexts'], ensure_ascii=False)); changed = True
        else:
            # Add editable UI labels for every language, while keeping values already customized by the owner.
            for key, value in SEED['siteTexts'].items():
                if key not in current['siteTexts']:
                    current['siteTexts'][key] = json.loads(json.dumps(value, ensure_ascii=False)); changed = True
                elif isinstance(current['siteTexts'][key], dict):
                    for language, text in value.items():
                        if language not in current['siteTexts'][key]:
                            current['siteTexts'][key][language] = text; changed = True
        # Seed a complete catalog if this is the old, incomplete starter database.
        if len(current.get('tours', [])) <= 3:
            for key in ('regions', 'tours', 'heroSlides'):
                current[key] = json.loads(json.dumps(SEED[key], ensure_ascii=False))
            changed = True
        else:
            # De-duplicate regions by canonical id or Georgian display name while preserving custom regions.
            seed_by_id = {str(x.get('id')): x for x in SEED.get('regions', [])}
            seed_by_name = {_localized_key(x): str(x.get('id')) for x in SEED.get('regions', [])}
            originals = current.get('regions', []) if isinstance(current.get('regions'), list) else []
            keep = []
            id_redirect = {}
            seen_names = {}
            seen_ids = {}
            for region in originals:
                if not isinstance(region, dict): continue
                old_id = str(region.get('id', '')).strip()
                name_key = _localized_key(region)
                canonical = old_id if old_id in seed_by_id else seed_by_name.get(name_key, old_id)
                if canonical in seen_ids:
                    id_redirect[old_id] = seen_ids[canonical]
                    changed = True
                    continue
                if name_key and name_key in seen_names:
                    id_redirect[old_id] = seen_names[name_key]
                    changed = True
                    continue
                if canonical in seed_by_id:
                    default = seed_by_id[canonical]
                    region['id'] = canonical
                    # Update only exact legacy stock/default images; keep photos the administrator selected.
                    if str(region.get('image', '') or '') in LEGACY_IMAGE_URLS or not str(region.get('image', '') or '').strip():
                        region['image'] = default.get('image', '')
                        region['imagePosition'] = default.get('imagePosition', 'center')
                        changed = True
                    if not region.get('name'): region['name'] = default.get('name', {})
                    if not region.get('description'): region['description'] = default.get('description', {})
                region['id'] = canonical or old_id or ('custom-region-' + str(len(keep)+1))
                keep.append(region)
                seen_ids[canonical] = region['id']
                if name_key: seen_names[name_key] = region['id']
            # Ensure every canonical Georgian region exists exactly once.
            keep_by_id = {str(x.get('id')): x for x in keep}
            for region in SEED.get('regions', []):
                rid = str(region.get('id'))
                if rid not in keep_by_id:
                    keep.append(json.loads(json.dumps(region, ensure_ascii=False)))
                    keep_by_id[rid] = keep[-1]
                    changed = True
            # Stable ordering: the 12 curated regions first, any unique admin-created regions afterward.
            standard_ids = [str(x.get('id')) for x in SEED.get('regions', [])]
            custom_regions = [x for x in keep if str(x.get('id')) not in standard_ids]
            ordered = [keep_by_id[rid] for rid in standard_ids if rid in keep_by_id] + custom_regions
            if ordered != originals: changed = True
            current['regions'] = ordered
            for tour in current.get('tours', []):
                if not isinstance(tour, dict): continue
                rid = str(tour.get('region', ''))
                if rid in id_redirect:
                    tour['region'] = id_redirect[rid]
                    changed = True
            # Add any missing built-in tour by id without deleting extra administrator-created tours.
            tours = current.setdefault('tours', [])
            existing_ids = {str(x.get('id')) for x in tours if isinstance(x, dict)}
            for default in SEED.get('tours', []):
                if str(default.get('id')) not in existing_ids:
                    tours.append(json.loads(json.dumps(default, ensure_ascii=False)))
                    changed = True
            # Refresh only known old seed assets (not arbitrary admin-selected or uploaded photos).
            for key in ('regions', 'tours'):
                default_by_id = {str(x.get('id')): x for x in SEED.get(key, [])}
                for item in current.get(key, []):
                    if not isinstance(item, dict): continue
                    default = default_by_id.get(str(item.get('id')))
                    if default and (str(item.get('image', '') or '') in LEGACY_IMAGE_URLS or not str(item.get('image', '') or '').strip()):
                        item['image'] = default.get('image', '')
                        item['imagePosition'] = default.get('imagePosition', 'center')
                        if default.get('imageFit'): item['imageFit'] = default['imageFit']
                        changed = True
            # Refresh the hero only when it still uses a URL shipped by the old seed.
            slides = current.setdefault('heroSlides', [])
            defaults = SEED.get('heroSlides', [])
            if not slides:
                current['heroSlides'] = json.loads(json.dumps(defaults, ensure_ascii=False))
                changed = True
            else:
                for idx, slide in enumerate(slides):
                    if idx < len(defaults) and isinstance(slide, dict) and (str(slide.get('image', '') or '') in LEGACY_IMAGE_URLS or not str(slide.get('image', '') or '').strip()):
                        slide['image'] = defaults[idx]['image']
                        slide['imagePosition'] = defaults[idx].get('imagePosition', 'center')
                        slide['title'] = defaults[idx]['title']
                        slide['subtitle'] = defaults[idx]['subtitle']
                        changed = True
        # Add the editable transfer/vehicle hero photo without overwriting an existing admin choice or an intentional blank.
        original_transfer_settings = json.dumps(current.get('transferSettings'), ensure_ascii=False, sort_keys=True)
        current['transferSettings'] = _normalise_transfer_settings(current.get('transferSettings'))
        if previous_site_version != APP_VERSION:
            current['transferSettings'] = _migrate_transfer_vehicle_slides(current['transferSettings'])
        if json.dumps(current.get('transferSettings'), ensure_ascii=False, sort_keys=True) != original_transfer_settings:
            changed = True
        if not isinstance(current.get('contact'), dict):
            current['contact'] = json.loads(json.dumps(SEED['contact'], ensure_ascii=False)); changed = True
        else:
            for key, value in SEED['contact'].items():
                if key not in current['contact']:
                    current['contact'][key] = value; changed = True
        # v8.5 restores a configurable WhatsApp contact button; preserve existing value and seed it only when missing.
        site_texts = current.get('siteTexts') if isinstance(current.get('siteTexts'), dict) else {}
        if 'whatsapp' in site_texts:
            site_texts.pop('whatsapp', None)
            changed = True
        field_contact = site_texts.get('fieldContact')
        if isinstance(field_contact, dict) and any('whatsapp' in str(value).casefold() for value in field_contact.values()):
            site_texts['fieldContact'] = json.loads(json.dumps(SEED['siteTexts']['fieldContact'], ensure_ascii=False))
            changed = True
        before_region_ids = [str(r.get('id')) for r in current.get('regions', []) if isinstance(r, dict)] if isinstance(current.get('regions'), list) else []
        before_region_names = [_localized_key(r) for r in current.get('regions', []) if isinstance(r, dict)] if isinstance(current.get('regions'), list) else []
        _dedupe_region_catalog(current)
        before_tour_ids = [str(t.get('id')) for t in current.get('tours', []) if isinstance(t, dict)] if isinstance(current.get('tours'), list) else []
        _dedupe_tour_catalog(current)
        after_region_ids = [str(r.get('id')) for r in current.get('regions', []) if isinstance(r, dict)]
        after_tour_ids = [str(t.get('id')) for t in current.get('tours', []) if isinstance(t, dict)]
        if before_region_ids != after_region_ids or len(before_region_names) != len(after_region_ids) or before_tour_ids != after_tour_ids:
            changed = True
        if current.get('siteVersion') != APP_VERSION:
            current['siteVersion'] = APP_VERSION
            changed = True
        if changed:
            con.execute('UPDATE content SET json=? WHERE id=1', (json.dumps(current, ensure_ascii=False),))
    except (TypeError, ValueError, KeyError, AttributeError):
        con.execute('UPDATE content SET json=? WHERE id=1', (json.dumps(SEED, ensure_ascii=False),))
    con.commit()
    return con

class Handler(BaseHTTPRequestHandler):
    server_version = 'GeoJoyLocal/8.9'

    def log_message(self, fmt, *args):
        print('[GeoJoy]', fmt % args)

    def send_bytes(self, data, typ='text/html; charset=utf-8', status=200, extra_headers=None):
        self.send_response(status)
        self.send_header('Content-Type', typ)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        self.send_header('Cache-Control','no-store')
        if extra_headers:
            for k,v in extra_headers.items(): self.send_header(k,v)
        self.end_headers()
        self.wfile.write(data)

    def json_response(self, obj, status=200, headers=None):
        self.send_bytes(json.dumps(obj, ensure_ascii=False).encode('utf-8'),'application/json; charset=utf-8',status,headers)

    def body(self):
        length = int(self.headers.get('Content-Length','0'))
        if length > 12_000_000: raise ValueError('Request too large')
        return self.rfile.read(length) if length else b''

    def session_ok(self):
        raw = self.headers.get('Cookie','')
        token = None
        for part in raw.split(';'):
            if part.strip().startswith('geojoy_session='):
                token = part.strip().split('=',1)[1]
        return token in SESSIONS if token else False

    def do_GET(self):
        p = urlparse(self.path).path
        if p in ('/','/index.html','/tours','/regions','/contact','/transfers','/about'):
            self.send_bytes((ROOT/'index.html').read_bytes())
        elif p in ('/photo-credits', '/photo-credits.html'):
            self.send_bytes((ROOT/'photo-credits.html').read_bytes())
        elif p in ('/admin','/admin/','/admin.html','/admin/index.html'):
            self.send_bytes((ROOT/'admin.html').read_bytes())
        elif p == '/api/health':
            self.json_response({'ok': True, 'version': APP_VERSION, 'adminPath': '/admin', 'port': int(os.environ.get('PORT','8052'))})
        elif p.startswith('/api/content'):
            con = connect_db(); row = con.execute('SELECT json FROM content WHERE id=1').fetchone(); con.close()
            self.json_response(json.loads(row['json']))
        elif p == '/api/admin/status':
            self.json_response({'authenticated': self.session_ok()})
        elif p == '/api/admin/content':
            if not self.session_ok(): return self.json_response({'error':'Unauthorized'},401)
            con=connect_db(); row=con.execute('SELECT json FROM content WHERE id=1').fetchone(); con.close(); self.json_response(json.loads(row['json']))
        elif p == '/api/admin/security/status':
            if not self.session_ok(): return self.json_response({'error':'Unauthorized'},401)
            con=connect_db()
            row=con.execute('SELECT recovery_hash,password_updated_at,recovery_updated_at FROM admin_security WHERE id=1').fetchone()
            con.close()
            self.json_response({'recoveryWordSet': bool(row and row['recovery_hash']),
                                'passwordUpdatedAt': row['password_updated_at'] if row else None,
                                'recoveryUpdatedAt': row['recovery_updated_at'] if row else None})
        elif p == '/api/admin/bookings':
            if not self.session_ok(): return self.json_response({'error':'Unauthorized'},401)
            con=connect_db(); rows=con.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall(); con.close(); self.json_response([dict(r) for r in rows])
        elif p in ('/styles.css', '/app.js', '/admin.css', '/admin.js'):
            target = ROOT / Path(p).name
            if not target.is_file(): return self.send_bytes(b'Not found','text/plain',404)
            self.send_bytes(target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        elif p.startswith('/uploads/'):
            name = Path(p).name
            target = UPLOADS / name
            if not target.exists() or not target.is_file(): return self.send_bytes(b'Not found','text/plain',404)
            self.send_bytes(target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        elif p.startswith('/static/'):
            name = Path(p).name
            if name not in STATIC_ASSETS: return self.send_bytes(b'Not found','text/plain',404)
            target = STATIC_DIR / name
            if not target.is_file(): target = ROOT / name
            if not target.is_file(): return self.send_bytes(b'Not found','text/plain',404)
            self.send_bytes(target.read_bytes(), mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        else:
            self.send_bytes(b'Not found','text/plain; charset=utf-8',404)

    def do_POST(self):
        p = urlparse(self.path).path
        try: raw = self.body()
        except ValueError as e: return self.json_response({'error':str(e)},413)
        try: data = json.loads(raw.decode('utf-8')) if raw else {}
        except Exception: return self.json_response({'error':'Invalid JSON'},400)
        if p == '/api/admin/login':
            supplied = str(data.get('password',''))
            if not _verify_admin_password(supplied): return self.json_response({'error':'პაროლი არასწორია'},401)
            token = secrets.token_urlsafe(32); SESSIONS.add(token)
            return self.json_response({'ok':True},200,{'Set-Cookie':f'geojoy_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800{COOKIE_SECURE_SUFFIX}'})
        if p == '/api/admin/security/change-password':
            if not self.session_ok(): return self.json_response({'error':'სესია ამოიწურა. თავიდან შედი.'},401)
            current_password = str(data.get('currentPassword',''))
            new_password = str(data.get('newPassword',''))
            confirm_password = str(data.get('confirmPassword',''))
            if not _valid_new_password(new_password):
                return self.json_response({'error':f'ახალი პაროლი მინიმუმ {MIN_PASSWORD_LENGTH} სიმბოლოს უნდა შეიცავდეს.'},400)
            if not _safe_compare_text(new_password, confirm_password):
                return self.json_response({'error':'ახალი პაროლები ერთმანეთს არ ემთხვევა.'},400)
            con=connect_db()
            row=con.execute('SELECT password_salt,password_hash FROM admin_security WHERE id=1').fetchone()
            if not row or not _verify_secret(current_password,row['password_salt'],row['password_hash']):
                con.close(); return self.json_response({'error':'მიმდინარე პაროლი არასწორია.'},403)
            salt,digest=_secret_hash(new_password)
            con.execute('UPDATE admin_security SET password_salt=?,password_hash=?,password_updated_at=CURRENT_TIMESTAMP WHERE id=1',(salt,digest))
            con.commit(); con.close()
            # Invalidate every old session, but issue a fresh session for the administrator who just changed it.
            SESSIONS.clear(); token=secrets.token_urlsafe(32); SESSIONS.add(token)
            return self.json_response({'ok':True,'message':'პაროლი წარმატებით შეიცვალა.'},200,{'Set-Cookie':f'geojoy_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800{COOKIE_SECURE_SUFFIX}'})
        if p == '/api/admin/security/set-recovery-word':
            if not self.session_ok(): return self.json_response({'error':'სესია ამოიწურა. თავიდან შედი.'},401)
            current_password=str(data.get('currentPassword',''))
            recovery_word=_normalize_recovery_word(data.get('recoveryWord',''))
            confirm_word=_normalize_recovery_word(data.get('confirmRecoveryWord',''))
            if len(recovery_word) < 6:
                return self.json_response({'error':'კოდური სიტყვა ან ფრაზა მინიმუმ 6 სიმბოლოს უნდა შეიცავდეს.'},400)
            if not _safe_compare_text(recovery_word,confirm_word):
                return self.json_response({'error':'კოდური სიტყვები ერთმანეთს არ ემთხვევა.'},400)
            con=connect_db()
            row=con.execute('SELECT password_salt,password_hash FROM admin_security WHERE id=1').fetchone()
            if not row or not _verify_secret(current_password,row['password_salt'],row['password_hash']):
                con.close(); return self.json_response({'error':'მიმდინარე პაროლი არასწორია.'},403)
            salt,digest=_secret_hash(recovery_word)
            con.execute('UPDATE admin_security SET recovery_salt=?,recovery_hash=?,recovery_updated_at=CURRENT_TIMESTAMP WHERE id=1',(salt,digest))
            con.commit(); con.close()
            return self.json_response({'ok':True,'message':'კოდური სიტყვა უსაფრთხოდ შეინახა. თავად სიტყვა ბაზაში ღია ტექსტად არ ინახება.'})
        if p == '/api/admin/security/recover-password':
            client=str(self.client_address[0])
            now=__import__('time').time()
            failures=RECOVERY_FAILURES.get(client)
            if failures and failures.get('lockedUntil',0)>now:
                wait=max(1,int(failures['lockedUntil']-now))
                return self.json_response({'error':f'ძალიან ბევრი მცდელობაა. სცადე {wait} წამში.'},429)
            recovery_word=_normalize_recovery_word(data.get('recoveryWord',''))
            new_password=str(data.get('newPassword',''))
            confirm_password=str(data.get('confirmPassword',''))
            if not _valid_new_password(new_password):
                return self.json_response({'error':f'ახალი პაროლი მინიმუმ {MIN_PASSWORD_LENGTH} სიმბოლოს უნდა შეიცავდეს.'},400)
            if not _safe_compare_text(new_password,confirm_password):
                return self.json_response({'error':'ახალი პაროლები ერთმანეთს არ ემთხვევა.'},400)
            con=connect_db()
            row=con.execute('SELECT recovery_salt,recovery_hash FROM admin_security WHERE id=1').fetchone()
            if not row or not row['recovery_hash']:
                con.close(); return self.json_response({'error':'კოდური სიტყვა ჯერ არ არის დაყენებული. სანამ პაროლის აღდგენა დაგჭირდება, შედი პანელში და უსაფრთხოების განყოფილებაში დააყენე.'},400)
            if not _verify_secret(recovery_word,row['recovery_salt'],row['recovery_hash']):
                con.close()
                failures=RECOVERY_FAILURES.setdefault(client,{'count':0,'lockedUntil':0})
                failures['count']=failures.get('count',0)+1
                if failures['count']>=5:
                    failures['lockedUntil']=now+300
                    failures['count']=0
                    return self.json_response({'error':'კოდური სიტყვა არასწორია. პაროლის აღდგენა დროებით შეიზღუდა 5 წუთით.'},429)
                return self.json_response({'error':'კოდური სიტყვა არასწორია.'},403)
            salt,digest=_secret_hash(new_password)
            con.execute('UPDATE admin_security SET password_salt=?,password_hash=?,password_updated_at=CURRENT_TIMESTAMP WHERE id=1',(salt,digest))
            con.commit(); con.close()
            SESSIONS.clear(); RECOVERY_FAILURES.pop(client,None)
            return self.json_response({'ok':True,'message':'პაროლი აღდგენილია. ახლა ახალი პაროლით შედი.'})
        if p == '/api/admin/logout':
            rawcookie=self.headers.get('Cookie','')
            for part in rawcookie.split(';'):
                if part.strip().startswith('geojoy_session='): SESSIONS.discard(part.strip().split('=',1)[1])
            return self.json_response({'ok':True},200,{'Set-Cookie':f'geojoy_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0{COOKIE_SECURE_SUFFIX}'})
        if p == '/api/bookings':
            required = ['kind','service','name','contact']
            if any(not str(data.get(k,'')).strip() for k in required): return self.json_response({'error':'გთხოვთ შეავსოთ სავალდებულო ველები.'},400)
            con=connect_db(); con.execute('INSERT INTO bookings(kind,service,date,pickup,destination,people,name,contact,note) VALUES(?,?,?,?,?,?,?,?,?)', tuple(str(data.get(k,''))[:1000] for k in ['kind','service','date','pickup','destination','people','name','contact','note'])); con.commit(); con.close()
            return self.json_response({'ok':True,'message':'მოთხოვნა მიღებულია. მადლობა!'},201)
        if p == '/api/admin/upload':
            if not self.session_ok(): return self.json_response({'error':'Unauthorized'},401)
            data_url = str(data.get('data',''))
            match = re.match(r'^data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)$', data_url)
            if not match: return self.json_response({'error':'ატვირთეთ PNG, JPG, WEBP ან GIF ფოტო.'},400)
            ext = 'jpg' if match.group(1) in ('jpeg','jpg') else match.group(1)
            payload=base64.b64decode(match.group(2))
            if len(payload) > 8_000_000: return self.json_response({'error':'ფოტო უნდა იყოს 8MB-ზე ნაკლები.'},413)
            filename=secrets.token_hex(12)+'.'+ext
            (UPLOADS/filename).write_bytes(payload)
            return self.json_response({'url':'/uploads/'+filename})
        return self.json_response({'error':'Not found'},404)

    def do_PUT(self):
        p=urlparse(self.path).path
        if p != '/api/admin/content': return self.json_response({'error':'Not found'},404)
        if not self.session_ok(): return self.json_response({'error':'Unauthorized'},401)
        try: raw=self.body(); data=json.loads(raw.decode('utf-8'))
        except Exception: return self.json_response({'error':'არასწორი მონაცემებია'},400)
        if not isinstance(data,dict) or not all(k in data for k in ('regions','tours','transfers','heroSlides','contact','about','brand','siteTexts')):
            return self.json_response({'error':'შინაარსის სტრუქტურა არასრულია'},400)
        data['transferSettings'] = _normalise_transfer_settings(data.get('transferSettings'))
        if not isinstance(data.get('contact'), dict):
            data['contact'] = {}
        for key in ('phone', 'telegram', 'whatsapp', 'email'):
            value = data['contact'].get(key, '')
            data['contact'][key] = str(value or '').strip()[:500]
        _dedupe_region_catalog(data)
        _dedupe_tour_catalog(data)
        # Send the normalized content back so the admin panel immediately reflects de-duplication.
        con=connect_db(); con.execute('UPDATE content SET json=? WHERE id=1',(json.dumps(data,ensure_ascii=False),)); con.commit(); con.close()
        return self.json_response({'ok':True,'message':'ცვლილებები შენახულია ამ კომპიუტერის მონაცემთა ბაზაში.','content':data})

    def do_PATCH(self):
        p=urlparse(self.path).path
        if p != '/api/admin/bookings': return self.json_response({'error':'Not found'},404)
        if not self.session_ok(): return self.json_response({'error':'Unauthorized'},401)
        try: data=json.loads(self.body().decode('utf-8'))
        except Exception: return self.json_response({'error':'Invalid JSON'},400)
        con=connect_db(); con.execute('UPDATE bookings SET status=? WHERE id=?',(str(data.get('status','New'))[:80],int(data.get('id',0)))); con.commit(); con.close()
        return self.json_response({'ok':True})

if __name__ == '__main__':
    connect_db().close()
    host=os.environ.get('HOST','127.0.0.1').strip() or '127.0.0.1'
    port=int(os.environ.get('PORT','8052'))
    print('\nGeoJoy is starting...')
    print('Public website: http://localhost:%s/'%port)
    print('Admin Panel:    http://localhost:%s/admin'%port)
    print('Bind address: %s:%s; use a TLS reverse proxy and firewall rules for public production access.\n'%(host,port))
    ThreadingHTTPServer((host,port),Handler).serve_forever()
