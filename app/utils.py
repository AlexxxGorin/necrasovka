def is_rus_language(phrase: str) -> bool:
    rus_alphabet = {
        "а",
        "б",
        "в",
        "г",
        "д",
        "е",
        "ё",
        "ж",
        "з",
        "и",
        "й",
        "к",
        "л",
        "м",
        "н",
        "о",
        "п",
        "р",
        "с",
        "т",
        "у",
        "ф",
        "х",
        "ц",
        "ч",
        "ш",
        "щ",
        "ъ",
        "ы",
        "ь",
        "э",
        "ю",
        "я",
    }
    return all(char in rus_alphabet for char in phrase.lower())


def transliterate(query: str) -> str:
    rus_to_eng_layout = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
    eng_to_rus_layout = {
        "a": "а",
        "b": "б",
        "c": "ц",
        "d": "д",
        "e": "е",
        "f": "ф",
        "g": "г",
        "h": "х",
        "i": "и",
        "j": "й",
        "k": "к",
        "l": "л",
        "m": "м",
        "n": "н",
        "o": "о",
        "p": "п",
        "q": "к",
        "r": "р",
        "s": "с",
        "t": "т",
        "u": "у",
        "v": "в",
        "w": "в",
        "x": "кс",
        "y": "й",
        "z": "з",
    }
    layout = rus_to_eng_layout if is_rus_language(query) else eng_to_rus_layout
    return "".join(layout.get(char, char) for char in query.lower())

def local_changer(query: str) -> str:
    layout = dict(
        zip(
            map(
                ord,
                """qwertyuiop[]asdfghjkl;'zxcvbnm,./`QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?~йцукенгшщзхъфывапролджэячсмитьбюёЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮЁ""",
            ),
            """йцукенгшщзхъфывапролджэячсмитьбю.ёЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,Ёqwertyuiop[]asdfghjkl;'zxcvbnm,.`QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>~""",
            strict=False,
        ),
    )
    return query.translate(layout)

def detect_publication_type(query: str) -> list[str]:
    """Определяет тип издания из запроса и возвращает ключевые слова для фильтрации"""
    query_lower = query.lower()
    
    publication_types = {
        'книга': ['книга', 'книги', 'том', 'тома', 'издание', 'сочинения'],
        'журнал': ['журнал', 'журналы', 'номер', '№', 'выпуск'],
        'газета': ['газета', 'газеты', 'ведомости', 'известия', 'правда'],
        'открытка': ['открытка', 'открытки', 'почтовая'],
        'спички': ['спички', 'спичечная', 'этикетка'],
        'плакат': ['плакат', 'плакаты', 'афиша'],
        'карта': ['карта', 'карты', 'план', 'атлас'],
    }
    
    detected_types = []
    for pub_type, keywords in publication_types.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_types.append(pub_type)
    
    return detected_types


def extract_clean_query(query: str) -> str:
    """Убирает из запроса слова типа издания, оставляя только основной поисковый запрос"""
    query_lower = query.lower()
    
    type_words = [
        'книга', 'книги', 'том', 'тома', 'издание', 'сочинения',
        'журнал', 'журналы', 'номер', '№', 'выпуск',
        'газета', 'газеты', 'ведомости', 'известия', 'правда',
        'открытка', 'открытки', 'почтовая',
        'спички', 'спичечная', 'этикетка',
        'плакат', 'плакаты', 'афиша',
        'карта', 'карты', 'план', 'атлас'
    ]
    
    words = query.split()
    clean_words = [word for word in words if word.lower() not in type_words]
    
    return ' '.join(clean_words) if clean_words else query


def coalesce(
    query: str,
    spelling_correction: str,
    local_changer: str,
    transliterate: str,
) -> list[str]:
    return list({query, transliterate})
    # return list({query, spelling_correction, local_changer, transliterate})
