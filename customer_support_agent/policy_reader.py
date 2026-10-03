import pypdf
import unicodedata

def read_policy(path):
    try:
        reader = pypdf.PdfReader(path)
        page_texts = []
        for page_number, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text()
            clean_text = unicodedata.normalize("NFKC", raw_text)
            clean_text = clean_text.replace(
                "أیام من تاریخ استلام الطلب.3یجب تقدیم طلب المتابعة خلال",
                "يجب تقديم طلب المتابعة خلال 3 أيام من تاريخ استلام الطلب."
                )
            clean_text = clean_text.replace(
                "أیام من الاستلام.3تقدیم الطلب بعد مرور أكثر من",
                "تقديم الطلب بعد مرور أكثر من 3 أيام من الاستلام."
                )
            clean_text = clean_text.replace(
                "أیام من الاستلام، توضّح لھ الأداة أن الطلب تجاوز مھلة المتابعة، دون إصدار قرار نھائي نیابة عن المتجر.5إذا أبلغ العمیل عن المشكلة بعد",
                "إذا أبلغ العميل عن المشكلة بعد 5 أيام من الاستلام، توضّح له الأداة أن الطلب تجاوز مهلة المتابعة، دون إصدار قرار نهائي نيابة عن المتجر."
                )
            clean_text = clean_text.replace(
                ". 3.draftیجھز التطبیق مسودة طلب متابعة بحالة",
                "3. يجهز التطبيق مسودة طلب متابعة بحالة draft."
                )
            clean_text = clean_text.replace(
                "وتعني أن الطلب ما زال تحت المراجعة، ولا تضمن قبول الاستبدال.draftلا، المسودة بحالة",
                "لا، المسودة بحالة draft وتعني أن الطلب ما زال تحت المراجعة، ولا تضمن قبول الاستبدال."
                )
            page_texts.append({
                "page": page_number,
                "text": clean_text,
                "raw_text": raw_text
            })

        return {
            "status": "success",
            "pages": len(reader.pages),
            "page_texts": page_texts
        }
    except FileNotFoundError as error:
        return {"status": "error", "message": "ملف السياسة غير موجود"}

def split_text(text, chunk_size):
    chunks = []
    for start in range(0, len(text), chunk_size):
        chunks.append(text[start:start + chunk_size])
    return chunks

def build_chunks(page_texts, chunk_size):
    records = []

    for page_data in page_texts:
        page_number = page_data["page"]
        page_chunks = split_text(page_data["text"], chunk_size)

        # اكتب حلقة المقاطع هنا
        for chunk_number, chunk_text in enumerate(page_chunks, start=1):
            chunk_id = f"p{page_number}-c{chunk_number}"
            records.append({
                "page": page_number,
                "text":chunk_text,
                "chunk_id": chunk_id
            })

    return records
