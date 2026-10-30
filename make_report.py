"""Створення Word-звіту: python make_report.py після main.py."""
from pathlib import Path
import csv
import json
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results'
NAVY = RGBColor(22, 47, 78)
TEAL = RGBColor(19, 134, 124)
GREY = RGBColor(83, 100, 114)


def set_cell_color(cell, color='EDF4F8'):
    tcPr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color)
    tcPr.append(shading)


def initialize():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2)
    sec.bottom_margin = Cm(1.8)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(1.8)
    sec.header_distance = Cm(.75)
    sec.footer_distance = Cm(.95)
    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'; normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.18
    normal.paragraph_format.space_after = Pt(7)
    for name,size in [('Title',21),('Heading 1',15),('Heading 2',13)]:
        st=doc.styles[name]
        st.font.name='Arial';st.font.size=Pt(size);st.font.bold=True;st.font.color.rgb=NAVY
        st.paragraph_format.space_before=Pt(10);st.paragraph_format.space_after=Pt(6)
    header=sec.header.paragraphs[0]
    header.text='КДПУ  /  ЛАБОРАТОРНА РОБОТА № 2'
    header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    for r in header.runs: r.font.name='Arial';r.font.size=Pt(8);r.font.color.rgb=GREY
    foot=sec.footer.paragraphs[0]
    foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    foot.add_run('Мінько Богдан  •  І-23    |    Сторінка ')
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');foot._p.append(fld)
    for r in foot.runs:r.font.name='Arial';r.font.size=Pt(8);r.font.color.rgb=GREY
    return doc


def para(doc, s='', bold_label=None):
    p=doc.add_paragraph()
    if bold_label and s.startswith(bold_label):
        p.add_run(bold_label).bold=True
        p.add_run(s[len(bold_label):])
    else:p.add_run(s)
    return p


def table(doc,headers,rows,width=None):
    t=doc.add_table(rows=1, cols=len(headers))
    t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for i,h in enumerate(headers):
        c=t.rows[0].cells[i];c.text=str(h);set_cell_color(c,'DCEDEB')
        for run in c.paragraphs[0].runs:
            run.bold=True;run.font.name='Arial';run.font.size=Pt(9);run.font.color.rgb=NAVY
    for ridx,row in enumerate(rows):
        cells=t.add_row().cells
        for i,value in enumerate(row):
            cells[i].text=str(value)
            cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if ridx%2==1:set_cell_color(cells[i],'F4F7FA')
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after=Pt(1)
                for r in p.runs:r.font.size=Pt(9.5)
    doc.add_paragraph().paragraph_format.space_after=Pt(0)
    return t


def add_figure(doc, name, caption, width=14.3):
    path = RESULTS / name
    if not path.exists():return
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Cm(width))
    cp=doc.add_paragraph(caption);cp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in cp.runs:r.font.size=Pt(9);r.font.italic=True;r.font.color.rgb=GREY


def csv_read(name,max_rows=None):
    path=RESULTS/name
    if not path.exists():return []
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    return rows if max_rows is None else rows[:max_rows]


def cover(doc, has_metrics):
    for _ in range(3):doc.add_paragraph('')
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run('КРИВОРІЗЬКИЙ ДЕРЖАВНИЙ\nПЕДАГОГІЧНИЙ УНІВЕРСИТЕТ')
    r.font.name='Arial';r.font.size=Pt(12);r.bold=True;r.font.color.rgb=NAVY
    doc.add_paragraph('')
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run('ЗВІТ\nДО ЛАБОРАТОРНОЇ РОБОТИ № 2')
    r.font.name='Arial';r.font.size=Pt(20);r.bold=True;r.font.color.rgb=TEAL
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run('Наївний баєсів класифікатор\nдля аналізу тональності текстів')
    r.font.name='Arial';r.font.size=Pt(15);r.bold=True;r.font.color.rgb=NAVY
    doc.add_paragraph('')
    p=para(doc,'Виконав: Мінько Богдан Сергійович\nГрупа: І-23\nСпеціальність: 122 «Інформатика»')
    p.paragraph_format.left_indent=Cm(7.5)
    for _ in range(4):doc.add_paragraph('')
    if not has_metrics:
        p=para(doc,'СТАН: робота підготовлена до запуску; фактичні результати будуть додані автоматично.')
        for r in p.runs:r.font.color.rgb=TEAL;r.bold=True
    p=doc.add_paragraph('Кривий Ріг — 2026');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()


def build_report(metrics=None):
    if metrics is None:
        mp=RESULTS/'metrics.json'
        metrics=json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else None
    finished = bool(metrics)
    doc=initialize();cover(doc,finished)
    doc.add_heading('1. Мета та завдання',level=1)
    para(doc,'Мета роботи — реалізувати наївний баєсів класифікатор для аналізу тональності англомовних твітів, перевірити його точність, дослідити інформативність слів і помилки передбачень, опублікувати інтерактивну вебсторінку.')
    para(doc,'Виконано програмну реалізацію попередньої обробки, словника частот, log prior та log likelihood, класифікації, тестування, аналізу слів і помилок, а також експорт моделі у JSON для GitHub Pages.')
    doc.add_heading('2. Дані та попередня обробка',level=1)
    para(doc,'Корпус: NLTK twitter_samples, файли positive_tweets.json і negative_tweets.json. Передбачено стратифіковане розділення: 80% для навчання, 20% для тестування; перемішування з фіксованим seed = 42. Для перевірки використовується незалежна тестова частина.')
    para(doc,'Функція process_tweet видаляє посилання, RT, позначення користувачів і тікери; зберігає текст хештегів, виконує токенізацію TweetTokenizer, вилучає стоп-слова і застосовує PorterStemmer. Заперечення (not, no тощо) збережено, оскільки вони можуть змінювати тональність.')
    doc.add_heading('3. Побудова словника та модель',level=1)
    para(doc,'Для кожного навчального твіту створено словник частот (основа слова, клас) → кількість появ. Далі обчислено log prior = ln(Dpos / Dneg) та log likelihood слова = ln(P(w|pos) / P(w|neg)). Для невідомих слів внесок у підсумковий бал дорівнює нулю.')
    para(doc,'Використано згладжування Лапласа: P(w|c) = (freq(w,c) + 1) / (N_c + |V|). Підсумковий бал твіту — сума log prior і log likelihood його слів. Якщо бал > 0, клас позитивний, інакше негативний.')
    if not finished:
        doc.add_heading('4. Результати (після запуску)',level=1)
        para(doc,'Фактичні показники ще не обчислено. Після виконання run_lab.bat програма згенерує папку results, файл docs/model.json і цей звіт з точністю, матрицею помилок, графіками та висновками. Не вказуйте жодні вигадані результати до запуску.')
    else:
        doc.add_heading('4. Результати навчання і тестування',level=1)
        table(doc,['Показник','Результат'],[
           ('Позитивних / негативних твітів',f'{metrics["positive_count"]} / {metrics["negative_count"]}'),
           ('Навчальних / тестових',f'{metrics["train_count"]} / {metrics["test_count"]}'),
           ('Кількість слів-основ у словнику',metrics['vocab_size']),
           ('Log prior',f'{metrics["logprior"]:.5f}'),
           ('Accuracy',f'{metrics["accuracy"]*100:.2f}%'),
           ('Precision',f'{metrics["precision"]:.4f}'),
           ('Recall',f'{metrics["recall"]:.4f}'),
           ('F1-score',f'{metrics["f1"]:.4f}'),
           ('Кількість помилок',metrics['errors'])])
        c=metrics['confusion_matrix']
        para(doc,f'Матриця помилок: TN={c[0][0]}, FP={c[0][1]}, FN={c[1][0]}, TP={c[1][1]}. Рядки — фактичні класи (0, 1); стовпці — передбачені класи (0, 1).')
        add_figure(doc,'confusion_matrix.png','Рис. 1. Матриця помилок класифікатора',10.6)
        doc.add_heading('5. Частотність і тонально забарвлені слова',level=1)
        para(doc,'Показник ratio = (count_pos + 1)/(count_neg + 1) використано для порівняння частот у класах. Ratio > 1 означає переважання слова у позитивному класі, ratio < 1 — у негативному. Окремо обчислено log likelihood з урахуванням загального числа слів у класах.')
        words=csv_read('word_frequencies.csv')
        if words:
            ranked=[w for w in words if int(w['positive'])+int(w['negative'])>=3]
            pos=sorted(ranked,key=lambda r:float(r['loglikelihood']),reverse=True)[:5]
            neg=sorted(ranked,key=lambda r:float(r['loglikelihood']))[:5]
            table(doc,['Клас','Основа слова','Позитивних','Негативних','Log likelihood'],[
               ('Позитивний',r['word'],r['positive'],r['negative'],r['loglikelihood']) for r in pos]+[
               ('Негативний',r['word'],r['positive'],r['negative'],r['loglikelihood']) for r in neg])
        add_figure(doc,'top_words.png','Рис. 2. Слова з найбільшим внеском у визначення тональності',13.3)
        doc.add_heading('6. Аналіз помилок класифікації',level=1)
        para(doc,f'У тестовій вибірці зафіксовано {metrics["errors"]} помилок. Хибнопозитивні (FP) — {c[0][1]}, хибнонегативні (FN) — {c[1][0]}. Нижче наведені приклади після токенізації та стемінгу (не вихідні публікації).')
        errors=csv_read('classification_errors.csv',5)
        if errors:
            table(doc,['Справжній','Прогноз','Бал','Токени (уривок)'],[
                ('pos' if r['truth']=='1' else 'neg',
                 'pos' if r['predicted']=='1' else 'neg',
                 r['score'], r['tokens'][:55]) for r in errors])
        para(doc,'Причини помилок можуть включати іронію, контекстні заперечення, короткі повідомлення, незнайомі слова та умовне припущення про незалежність слів. Самі припущення потрібно зіставляти з конкретними помилковими прикладами.')
        doc.add_heading('7. Власні твіти',level=1)
        examples=csv_read('own_tweets.csv')
        if examples:
            table(doc,['Текст','Log score','Передбачення'],[
                (r['tweet'],r['log_score'],r['predicted']) for r in examples])
        doc.add_heading('8. Вебсторінка та експорт моделі',level=1)
        para(doc,'Після навчання автоматично створюється docs/model.json із параметрами моделі (logprior, loglikelihood) і відповідністю поверхневих токенів їхнім основам. Вебсторінка docs/index.html читає JSON, дозволяє вводити власний англомовний твіт, виводить клас, бал, умовну ймовірність і слова, що вплинули на прогноз.')
        para(doc,'Важливе обмеження: для вебверсії експортовано відповідність основ для слів, відомих навчанню. Незнайомі форми слів можуть ігноруватися; JavaScript-токенізація є наближенням TweetTokenizer. Для повної тотожності з Python потрібен спеціальний порт токенізатора і стемера.')
        doc.add_heading('9. Висновки',level=1)
        para(doc,f'Реалізовано власний класифікатор Naive Bayes без використання готового класифікатора з бібліотек машинного навчання. На {metrics["test_count"]} відкладених прикладах точність становить {metrics["accuracy"]*100:.2f}%, F1 — {metrics["f1"]:.4f}. Аналіз {metrics["errors"]} помилкових рішень і співвідношень частот слів показує, що модель корисна для базового аналізу тональності, але має обмеження для складних конструкцій і нової лексики.')
    doc.add_heading('10. Публікація та джерела' if finished else '5. Публікація та джерела',level=1)
    para(doc,'Після завантаження на GitHub у Moodle надаються два посилання: (1) репозиторій із кодом, звітом і результатами; (2) інтерактивна сторінка GitHub Pages. Адреси дописуються після фактичної публікації.')
    para(doc,'Документація NLTK: https://www.nltk.org/howto/twitter.html')
    para(doc,'Офіційні дані NLTK: https://www.nltk.org/data.html')
    para(doc,'Довідка GitHub Pages: https://docs.github.com/en/pages')
    out=ROOT/'Lab2_Report.docx'
    doc.save(out)
    return out

if __name__=='__main__':
    output=build_report()
    print(f'Збережено: {output}')
