import os
import re
import fitz
import argparse
import sqlite3 as sl


def pdf_find(path):
    """ Ищем pdf документы и их верные идентификаторы """
    documents = os.listdir(path)
    result_documents = []
    result_pages = []
    title_num = []
    id_of_documents = []
    for document in documents:

        # finding doc with pdf extension
        if document.split(".")[-1].lower() == "pdf":

            # pattern for document id
            match = re.search(r'(?:СТО|Р) Газпром (?:РД ){0,1}[\.\d]{1,7}(?:-[\.\d]{1,4}){0,1}(?:-\d{1,4}){0,1}-\d{4}',
                              document)
            id_document = match[0] if match else None

            # Если у документа верный идентификатор, то вызываем функцию для поиска оглавления и нужного пункта меню
            if id_document is not None:
                id_of_documents.append(id_document)
                use_func = find_terms(path, document)
                result_pages.append(use_func[0])
                title_num.append(use_func[1])
                result_documents.append(document)
    return result_documents, result_pages, title_num, id_of_documents


def find_terms(path, document):
    """
    Ищем пункт меню Термины и определения
    :returns Возвращает начальную и конечную страницу с терминами
    """
    document_root_path = os.path.join(path, document)
    pdf_document = fitz.open(document_root_path)

    # defining terms that doc must have in
    first_cond = "Термины"
    second_cond = "определения"

    # define start_page and end_page
    term_start_page = -1
    term_end_page = -1

    # iterating by page to find start_page and end_page
    count = 0
    res = []
    for current_page in range(len(pdf_document)):
        page = pdf_document.load_page(current_page)
        page_text = page.get_text().replace(" ", "").replace(".", "").split("\n")
        for word in page_text:
            if word == "Содержание":
                count += 1
                res = page_text
                break
            if count > 0:
                break

    # Идем по пунктам меню (если пункт не будет найден, то значение останется -1)
    title_num = 0
    for i in range(len(res)):
        if first_cond in res[i] and second_cond in res[i]:
            tmp = 0
            try:
                title_num = int(res[i][0])
            except ValueError:
                title_num = int(res[i - 1])
            try:
                term_start_page = int(res[i][-1])
                tmp = i + 1
            except ValueError:
                term_start_page = int(res[i + 1])
                tmp = i + 2
            for y in range(tmp, len(res)):
                try:
                    if int(res[y][0]) == title_num + 1:
                        try:
                            term_end_page = int(res[y][-1])
                            break
                        except ValueError:
                            try:
                                term_end_page = int(res[y + 1])
                            except ValueError:
                                term_end_page = int(res[y + 2])
                            break
                except ValueError:
                    term_end_page = int(res[y][-2] + res[y][-1])
                    break
            break
    result_pages = [term_start_page, term_end_page]

    # Если нет оглавления - ставим в страницы значение -2
    if count == 0:
        result_pages = [-2, -2]
    return result_pages, title_num


def get_all_pages(document_path, doc_pages):
    """ Получаем номера страниц с терминами """
    pdf_document = fitz.Document(document_path)
    pages_in_doc = []
    for current_page in range(len(pdf_document)):
        page = pdf_document.load_page(current_page)
        arr = page.get_text().replace(" ", "").replace(".", "").split("\n")
        rev_arr = list(reversed(arr))
        for i in range(doc_pages[0], doc_pages[1] + 1):
            if len(arr) > 1 and (arr[0].strip() == str(i) or arr[1].strip() == str(i)):
                pages_in_doc.append(current_page)
                break
            pattern = re.compile("\d")
            if len(rev_arr) > 1 and rev_arr[1] == str(i) and arr[0].strip() != str(i) and \
                    re.fullmatch(pattern, rev_arr[-1]) is None:
                pages_in_doc.append(current_page)
                break
    return pages_in_doc


def analyze_text(document_path, pages_in_doc, chapter):
    """ Анализируем страницы и ищем коды, термины, определения и ссылки """
    # print(document_path)
    pdf_document = fitz.Document(document_path)
    all_separators = []
    all_text = []
    for page_num in pages_in_doc:
        page = pdf_document.load_page(page_num)
        text = page.get_text().rsplit(":")
        new_text = []
        for i in range(len(text)):
            new_text.append(text[i].replace("\n", " ").replace("- ", ""))
        pattern = re.compile(f"(\s{chapter}\.[1-9]+\s+)|\s({chapter}\.[1-9]\.[1-9]+\s+)")
        for i in range(len(new_text)):
            match = re.findall(pattern, new_text[i])
            res = match[0] if match else None
            all_separators.append(res)
            all_text.append(new_text[i])
    while True:
        if all_separators and all_separators[0] is None:
            del all_separators[0]
            del all_text[0]
        else:
            break
    while True:
        if all_separators and all_separators[-1] == all_separators[-2]:
            del all_separators[-1]
            del all_text[-1]
        else:
            break
    if all_separators and all_separators[0] and all_separators[1] and all_separators[0][1] == all_separators[1][0]:
        del all_separators[0]
        del all_text[0]
    term_code = []

    while True:
        count = 0
        for i in range(len(all_text)):
            count += 1
            if len(all_text[i]) < 20:
                del all_text[i]
                del all_separators[i]
                break
        if count == len(all_text):
            break

    check_sep = []
    check_text = []
    while True:
        count = 1
        if all_separators:
            for i in range(1, len(all_separators)):
                count += 1
                if all_separators[i] and all_separators[i - 1] and all_separators[i][1] == all_separators[i - 1][0]:
                    check_text.append(all_text[i].split(all_separators[i][0])[0].strip())
                    check_sep.append(all_separators[i - 1][1])
                    del all_separators[i]
                    del all_text[i]
                    break
        else:
            break
        if count == len(all_separators):
            break

    for i in range(len(all_separators)):
        if all_separators[i] and len(all_separators[i][0]) > 0:
            term_code.append(all_separators[i][0].strip())
        elif all_separators[i] and len(all_separators[i][1]) > 0:
            term_code.append(all_separators[i][1].strip())
        else:
            term_code.append("")

    result_terms = []
    result_term_codes = []
    result_term_defs = []

    if term_code and len(term_code[0]) > 0:
        result_term_codes.append(term_code[0].strip())
        result_terms.append(all_text[0].split(term_code[0])[1].strip())

    a = True
    while True:
        count = 0
        for i in range(1, len(term_code) - 1):
            if len(term_code[i]) == 0 and len(term_code[i-1]) > 0:
                new = term_code[i-1].split(".")
                new_num = ""
                new1 = term_code[i - 1].split(".")
                new_num1 = ""
                for z in range(len(new) - 1):
                    new_num += new[z] + "."
                for z in range(len(new) - 2):
                    new_num1 += new[z] + "."
                new_num += str(int(new[len(new) - 1]) + 1)
                new_num1 += str(int(new[len(new) - 2]) + 1) + "." + str(1)
                if new_num in all_text[i]:
                    term_code[i] = new_num
                    count += 1
                    break
                elif new_num1 in all_text[i]:
                    term_code[i] = new_num1
                    count += 1
                    break
            if len(term_code[i]) == 0 and len(term_code[i - 1]) == 0:
                new = term_code[i - 2].split(".")
                new_num = ""
                new1 = term_code[i - 2].split(".")
                new_num1 = ""
                for z in range(len(new) - 1):
                    new_num += new[z] + "."
                for z in range(len(new) - 2):
                    new_num1 += new[z] + "."
                new_num += str(int(new[len(new) - 1]) + 1)
                new_num1 += str(int(new[len(new) - 2]) + 1) + "." + str(1)
                if new_num in all_text[i]:
                    term_code[i] = new_num
                    count += 1
                    break
                elif new_num1 in all_text[i]:
                    term_code[i] = new_num1
                    count += 1
                    break
        if count == 0:
            break

    for i in range(1, len(term_code) - 1):
        if len(term_code[i]) == 0 and len(term_code[i-1]) > 0:
            result_term_defs.append(all_text[i].strip())
        elif len(term_code[i]) > 0 and len(term_code[i-1]) == 0:
            if "Газпром" in all_text[i].split(term_code[i])[0]:
                result_term_codes.append(term_code[i].strip())
                result_terms.append(all_text[i].split(term_code[i])[1].strip())
            else:
                result_term_codes.append(term_code[i].strip())
                result_terms.append(all_text[i].split(term_code[i])[1].strip())
                result_term_defs.append(all_text[i].split(term_code[i])[0].strip())
        else:
            try:
                result_term_codes.append(term_code[i].strip())
                result_terms.append(all_text[i].split(term_code[i])[1].strip())
                result_term_defs.append(all_text[i].split(term_code[i])[0].strip())
            except ValueError:
                pass
    try:
        result_term_defs.append(all_text[len(all_text) - 1].split(" " + str(chapter + 1) + " ")[0].strip())
    except IndexError:
        pass

    term_code = []
    term = []
    term_def = []
    term_reference = []

    # filling result arrays of terms/code/definitions
    for i, j, k in zip(result_term_codes, result_terms, result_term_defs):
        term_code.append(i.strip())
        term.append(j.replace("� ", "").replace("  ", " ").replace("�", "").strip())
        term_def.append(k.replace("� ", "").replace("  ", " ").replace("�", "").strip())

    pattern_reference_start = re.compile("\[")
    pattern_reference_end = re.compile("]")
    start = 0
    end = 0
    for y, item in enumerate(term_def):
        for i, match_start in enumerate(re.finditer(pattern_reference_start, item)):
            if i == 0:
                start = match_start.start()
        for match_end in re.finditer(pattern_reference_end, item):
            end = match_end.end()

        if start != 0 and end != 0 and len(item[start:end]) > 0:
            term_reference.append(item[start:end])
            term_def[y] = term_def[y][:end]
        else:
            term_reference.append("")

    return term_code, term, term_def, term_reference


def argument_parser():
    """ Parsing command line arguments """
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', '-d', help="input path to root dir with pdf files")
    my_namespace = parser.parse_args()
    directory_path = my_namespace.dir
    return directory_path


def db_creating(file_id, file_path, doc, doc_id, terms_start_page, terms_end_page, term_code, term, term_def, term_reference):
    """ Создание базы данных и заполнение итоговых результатов"""

    con = sl.connect('result_db.db')
    try:
        with con:

            # Таблица документов
            con.execute("""
                CREATE TABLE document (
                    file_id INTEGER NOT NULL PRIMARY KEY,
                    filepath VARCHAR(500) NOT NULL,
                    filename VARCHAR(100) NOT NULL,
                    document_id VARCHAR(100),
                    terms_start_page INTEGER,
                    terms_end_page INTEGER);
                        """)

            # Таблица терминов
            con.execute("""
                            CREATE TABLE term (
                            file_id INTEGER NOT NULL,
                            term_code VARCHAR(10),
                            term VARCHAR(500),
                            term_def VARCHAR(5000),
                            term_reference VARCHAR(100),
                            CONSTRAINT c_term_pk PRIMARY KEY (file_id, term),
                            CONSTRAINT c_term_fk FOREIGN KEY (file_id) REFERENCES document (file_id));
                                                """)

            # Таблица ошибок
            con.execute("""
                                        CREATE TABLE processing_error (
                                            file_id INTEGER NOT NULL,
                                            message VARCHAR(5000) NOT NULL,
                                            CONSTRAINT c_processing_error_fk FOREIGN KEY (file_id) REFERENCES document (file_id));
                                                """)

    except sl.OperationalError:
        pass

    # Вставка результатов в таблицу документов
    sql_document = 'INSERT OR IGNORE INTO document (file_id, filepath, filename, document_id, terms_start_page, terms_end_page) values(?, ?, ?, ?, ?, ?)'
    data_document = [
        (file_id, file_path, doc, doc_id, terms_start_page, terms_end_page)
    ]
    with con:
        con.executemany(sql_document, data_document)

    # Если с документом все нормально - заполняем термины
    if terms_start_page > -1:
        for i in range(len(term)):
            sql_term = 'INSERT OR IGNORE INTO term (file_id, term_code, term, term_def, term_reference) values(?, ?, ?, ?, ?)'
            data_term = [
                (file_id, str(term_code[i]), str(term[i]), str(term_def[i]), str(term_reference[i]))
            ]
            with con:
                con.executemany(sql_term, data_term)

    # Если у документа отсутствует пункт Термины и определения
    elif terms_start_page == -1:
        sql_proc_error = 'INSERT OR IGNORE INTO processing_error (file_id, message)  values(?, ?)'
        data_proc_error = [
            (file_id, "Не найден пункт Термины и определения")
        ]
        with con:
            con.executemany(sql_proc_error, data_proc_error)

    # Если у документа отсутствует оглавление
    elif terms_start_page == -2:
        sql_proc_error = 'INSERT OR IGNORE INTO processing_error (file_id, message)  values(?, ?)'
        data_proc_error = [
            (file_id, "Не найдено оглавление")
        ]
        with con:
            con.executemany(sql_proc_error, data_proc_error)


if __name__ == "__main__":
    root_path = argument_parser()
    dirs = os.listdir(root_path)
    idx = 0
    for directory in dirs:
        folder_path = os.path.join(root_path, directory)
        doc_and_pages = pdf_find(folder_path)
        for doc, pages, sep, doc_id in zip(doc_and_pages[0], doc_and_pages[1], doc_and_pages[2], doc_and_pages[3]):

            file_id = idx
            document_id = doc
            file_path = os.path.join(folder_path, doc)
            terms_start_page = pages[0]
            terms_end_page = pages[1]
            term_code = []
            term = []
            term_def = []
            term_reference = []
            if pages[0] != -1 and pages[0] != -2:
                doc_path = os.path.join(folder_path, doc)
                terms_start_page = pages[0]  # Итоговая начальная страница
                terms_end_page = pages[1]  # Итоговая конечная страница
                pages_in_document = get_all_pages(doc_path, pages)
                extract = analyze_text(doc_path, pages_in_document, sep)
                term_code = extract[0]  # Итоговый коды терминов
                term = extract[1]  # Итоговые термины
                term_def = extract[2]  # Итоговые определения терминов
                term_reference = extract[3]  # Итоговые сыллки у терминов

                # Убираем ошибочно добавленные ссылки
                for i in range(len(term_reference)):
                    if "[" not in term_reference[i] and "]" not in term_reference[i]:
                        term_reference[i] = ""
                    if len(term_reference[i]) < 5:
                        term_reference[i] = ""

            # ВЫзываем функцию для работы с БД
            db_creating(file_id, file_path, doc, doc_id, terms_start_page, terms_end_page, term_code, term, term_def,
                        term_reference)
            idx += 1
    print("All data has been inserted")
