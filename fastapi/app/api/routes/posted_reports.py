from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from datetime import timedelta
from db import postgres_connection
from schemas import response_body
from schemas import request_body

from fastapi.responses import FileResponse, JSONResponse
import mimetypes
import pytz
import os
import json
import io
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from schemas.models import Infra as InfraModel
from schemas.models import ReportForm as ReportFormModel
from schemas.models import PostedReport as PostedReportModel
from schemas.models import ImgFile as ImgFileModel
from db.postgres_connection import connect_db
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy import delete
from db.minio_connection import minio_client
from datetime import datetime
from fastapi.responses import StreamingResponse
from sqlalchemy import Integer
import time
from schemas.response_body import ReportResponseModel, PostedReportResponseModel, PostedReportsResponseModel

from reportlab.lib.units import inch
from PIL import Image
import io

import requests
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import urllib.parse

router = APIRouter()


# 설비에 해당하는 보고서 제출 목록 가져오기 (날짜 기준 오름차순)
@router.get("/api/posted-reports", summary="보고서 목록 조회(AND)", description="설비와 회사 이름을 기준으로 보고서 제출 목록을 날짜 기준 오름차순으로 반환합니다.(DB 데이터 - 실제 json data X)"
            ,response_model = PostedReportsResponseModel )
async def get_posted_reports(
    infra: str = None, company_name: str = None, db: AsyncSession = Depends(connect_db)
):
    if not infra:
        raise HTTPException(
            status_code=400, detail="Infra name is missing in query parameters"
        )
    if not company_name:
        raise HTTPException(
            status_code=400, detail="Company name is missing in query parameters"
        )

    try:
        infra_result = await db.execute(
            select(InfraModel.infra_id).where(
                InfraModel.infra_name == infra, InfraModel.company_name == company_name
            )
        )
        infra_id = infra_result.scalars().first()

        if not infra_id:
            raise HTTPException(
                status_code=404,
                detail=f'Infra "{infra}" not found for company "{company_name}"',
            )

        # 보고서 제출 목록 조회
        reports_result = await db.execute(
            select(PostedReportModel)
            .join(
                ReportFormModel,
                PostedReportModel.report_form_id == ReportFormModel.report_form_id,
            )
            .where(ReportFormModel.infra_id == infra_id)
            .order_by(PostedReportModel.start_time.asc())
        )

        reports = reports_result.scalars().all()

        # 보고서 목록을 JSON 응답으로 반환
        reports_list = [
            {
                "posted_report_id": report.posted_report_id,
                "posted_report_path": report.posted_report_path,
                "user_name": report.user_name,
                "start_time": report.start_time,
                "end_time": report.end_time,
                "company_name": report.company_name,
                "memo": report.memo
            }
            for report in reports
        ]

        return JSONResponse(content={"posted_reports": reports_list}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# 설비의 특정 날짜 보고서 가져오기
@router.get("/api/posted-report-by-date", summary="특정 날짜의 보고서 조회(AND)", description="설비와 회사 이름, 특정 Unix 시간을 기준으로 보고서를 반환합니다."
            ,response_model = PostedReportsResponseModel)
async def get_posted_report_by_date(
    infra: str = None,
    company_name: str = None,
    Unixtime: int = None,
    db: AsyncSession = Depends(connect_db),
):
    if not infra:
        raise HTTPException(
            status_code=400, detail="Infra name is missing in query parameters"
        )
    if not company_name:
        raise HTTPException(
            status_code=400, detail="Company name is missing in query parameters"
        )
    if not Unixtime:
        raise HTTPException(
            status_code=400, detail="Unixtime is missing in query parameters"
        )

    try:
        # infra_id 가져오기
        infra_id_result = await db.execute(
            select(InfraModel.infra_id).where(
                InfraModel.infra_name == infra, InfraModel.company_name == company_name
            )
        )
        infra_id = infra_id_result.scalars().first()

        if not infra_id:
            raise HTTPException(
                status_code=404,
                detail=f'Infra "{infra}" not found for company "{company_name}"',
            )

        # 특정 날짜에 해당하는 보고서 조회
        reports_result = await db.execute(
            select(PostedReportModel)
            .join(
                ReportFormModel,
                PostedReportModel.report_form_id == ReportFormModel.report_form_id,
            )
            .where(
                ReportFormModel.infra_id == infra_id,
                PostedReportModel.start_time <= Unixtime,
                PostedReportModel.end_time >= Unixtime,
            )
        )

        reports = reports_result.scalars().all()

        # 보고서 목록을 JSON 응답으로 반환
        reports_list = [
            {
                "posted_report_id": report.posted_report_id,
                "posted_report_path": report.posted_report_path,
                "user_name": report.user_name,
                "start_time": report.start_time,
                "end_time": report.end_time,
                "company_name": report.company_name,
                "memo" : report.memo
            }
            for report in reports
        ]

        return JSONResponse(content={"posted_reports": reports_list}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# minio에 저장된 특정 보고서 하나 가져오기 (Deprecated)
@router.get("/api/posted-report/deprecated", summary="MinIO에 저장된 보고서 조회 (Deprecated) (AND)", description="MinIO에 저장된 특정 보고서를 조회합니다."
            ,response_model =ReportResponseModel
            ,include_in_schema=False)
async def get_posted_report_from_minio(posted_report_id: int = None):
    if not posted_report_id:
        raise HTTPException(
            status_code=400, detail="posted_report_id is missing in query parameters"
        )
    try:
        bucket_name = os.environ["MINIO_BUCKET"]
        objects = minio_client.list_objects(bucket_name)
        for obj in objects:
            print(obj.object_name)

        file_name = f"{posted_report_id}.json"
        response = minio_client.get_object(bucket_name, file_name)
        file_data = response.read()
        response.close()
        response.release_conn()

        file_type, _ = mimetypes.guess_type(file_name)

        file_stream = io.BytesIO(file_data)
        return StreamingResponse(
            file_stream,
            media_type=file_type if file_type else "application/octet-stream",
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# infra, company_name에 따른 작성된 보고서를 Minio에서 가져오기
@router.get("/api/posted-report", summary="설비와 회사 이름에 따른 가장 최근 보고서 조회(AND)", description="설비와 회사 이름을 기준으로 MinIO에 가장 최근에 저장된 보고서를 가져옵니다."
            ,response_model = ReportResponseModel)
async def get_posted_report_from_minio_with_infra_company_name(
    infra: str = None, company_name: str = None, db: AsyncSession = Depends(connect_db)
):
    if not infra:
        raise HTTPException(
            status_code=400, detail="Infra name is missing in query parameters"
        )
    if not company_name:
        raise HTTPException(
            status_code=400, detail="Company name is missing in query parameters"
        )

    try:
        infra_id_result = await db.execute(
            select(InfraModel.infra_id).where(
                InfraModel.infra_name == infra, InfraModel.company_name == company_name
            )
        )
        infra_id = infra_id_result.scalars().first()

        if not infra_id:
            raise HTTPException(
                status_code=404,
                detail=f'Infra "{infra}" not found for company "{company_name}"',
            )

        last_number_result = await db.execute(
            select(PostedReportModel.posted_report_id)
            .join(
                ReportFormModel,
                ReportFormModel.report_form_id == PostedReportModel.report_form_id,
            )
            .where(ReportFormModel.infra_id == infra_id)
            .order_by(
                PostedReportModel.posted_report_id.desc()
            )  
            .limit(1)  
        )

        last_number = last_number_result.scalar()

        if not last_number:
            raise HTTPException(
                status_code=404,
                detail=f'No report found for infra "{infra}" and company "{company_name}"',
            )

        bucket_name = os.environ["MINIO_BUCKET"]
        file_name = f"{last_number}.json"
        response = minio_client.get_object(bucket_name, file_name)

        data = response.read()
        response.close()
        response.release_conn()

        data_str = data.decode("utf-8")
        report_data = json.loads(data_str)

        return JSONResponse(
            content={"message": "Report fetched successfully", "report": report_data},
            status_code=200,
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# minio에 저장된 특정 보고서 하나 가져오기
@router.get("/api/posted-reports-detail", summary="특정 보고서 상세 조회(AND)", description="설비와 회사 이름, 보고서 ID를 기준으로 MinIO에 저장된 특정 보고서를 조회합니다." 
            ,response_model = ReportResponseModel)
async def get_posted_reports_detail(
    infra: str, company_name: str, posted_report_id: int
):
    if not infra:
        raise HTTPException(
            status_code=400, detail="Infra name is missing in query parameters"
        )
    if not company_name:
        raise HTTPException(
            status_code=400, detail="company_name is missing in query parameters"
        )
    if not posted_report_id:
        raise HTTPException(
            status_code=400, detail="posted_report_id is missing in query parameters"
        )
    try:
        file_name = str(posted_report_id) + '_' + infra + "_" + company_name
        bucket_name = os.environ["MINIO_BUCKET"]
        response = minio_client.get_object(bucket_name, file_name)

        data = response.read()
        response.close()
        response.release_conn()

        data_str = data.decode("utf-8")
        report_data = json.loads(data_str)

        return JSONResponse(
            content={"message": "Report fetched successfully", "report": report_data},
            status_code=200,
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/api/posted-reports-detail-pdf", summary="특정 보고서 상세 조회(PDF)", description="설비와 회사 이름, 보고서 ID를 기준으로 MinIO에 저장된 특정 보고서를 PDF로 변환하여 조회합니다.")
async def get_posted_reports_detail_pdf(
    infra: str, company_name: str, posted_report_id: int, db: AsyncSession = Depends(connect_db)
):
    if not infra:
        raise HTTPException(
            status_code=400, detail="Infra name is missing in query parameters"
        )
    if not company_name:
        raise HTTPException(
            status_code=400, detail="company_name is missing in query parameters"
        )
    if not posted_report_id:
        raise HTTPException(
            status_code=400, detail="posted_report_id is missing in query parameters"
        )
    
    try:
        file_name = str(posted_report_id) + '_' + infra + "_" + company_name
        bucket_name = os.environ["MINIO_BUCKET"]
        response = minio_client.get_object(bucket_name, file_name)

        data = response.read()
        response.close()
        response.release_conn()

        data_str = data.decode("utf-8")
        report_data = json.loads(data_str)

        pdf_buffer = BytesIO()

        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        pdfmetrics.registerFont(TTFont("NotoSansKR-Medium", "/usr/share/fonts/opentype/noto/NotoSansKR-Medium.ttf"))
        pdfmetrics.registerFont(TTFont("NotoSansKR-Light", "/usr/share/fonts/opentype/noto/NotoSansKR-Light.ttf"))

        c.setFont("NotoSansKR-Medium", 12)
        basic_info = [
            ["Report ID", posted_report_id],
            ["설비 이름", infra],
            ["회사 이름", company_name],
            ["작성 시작 시간", report_data.get("start_time", "N/A")],
            ["작성 완료 시간", report_data.get("end_time", "N/A")],
            ["사용자", report_data.get("user_name", "N/A")],
        ]
        table = Table(basic_info, colWidths=[2 * inch, 4 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, -1), "NotoSansKR-Medium"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        table.wrapOn(c, 100, 750)
        table.drawOn(c, 100, 650)
        y_position = 620
        page_threshold = 50  # 페이지 전환 임계값
        image_height = 120  # 이미지 높이 설정

        inspection_list = report_data.get("inspection_list", [])
        for i, topic in enumerate(inspection_list):
            c.setFont("NotoSansKR-Medium", 10)
            c.drawString(100, y_position, f"Topic {i + 1}: {topic['topic']}")
            y_position -= 20

            if y_position < page_threshold:
                c.showPage()
                y_position = 750

            for instruction in topic["instruction_list"]:
                c.setFont("NotoSansKR-Medium", 10)
                c.drawString(120, y_position, "Instruction:")
                c.setFont("NotoSansKR-Light", 10)
                c.drawString(180, y_position, instruction['instruction'])
                y_position -= 15

                c.setFont("NotoSansKR-Medium", 10)
                c.drawString(120, y_position, "Type:")
                c.setFont("NotoSansKR-Light", 10)
                c.drawString(180, y_position, instruction['instruction_type'])
                y_position -= 15

                if instruction["options"]:
                    c.setFont("NotoSansKR-Medium", 10)
                    c.drawString(120, y_position, "Options:")
                    c.setFont("NotoSansKR-Light", 10)
                    c.drawString(180, y_position, ", ".join(instruction['options']))
                    y_position -= 15

                c.setFont("NotoSansKR-Medium", 10)
                c.drawString(120, y_position, "Answer:")
                c.setFont("NotoSansKR-Light", 10)
                c.drawString(180, y_position, ", ".join(instruction['answer']))
                y_position -= 50

                if instruction["img_url"]:
                    try:
                        file_id = int(instruction["img_url"].split("/")[-1])
                        
                        result = await db.execute(
                            select(ImgFileModel).where(ImgFileModel.file_id == file_id)
                        )
                        image_record = result.scalars().first()
                        
                        if image_record and image_record.file_data:
                            image = Image.open(io.BytesIO(image_record.file_data))
                            if image.mode == 'RGBA':
                                image = image.convert('RGB')
            
                            image.thumbnail((3 * inch, 2 * inch))  
                            image_path = f"/tmp/{file_id}.jpg"
                            image.save(image_path, format="JPEG")

                            if y_position < page_threshold + image_height:
                                c.showPage()
                                y_position = 750

                            c.drawImage(image_path, 120, y_position - image_height, width=3 * inch, height=2 * inch)
                            y_position -= image_height  
                        else:
                            c.drawString(120, y_position, "Image not found in database.")
                            y_position -= 20

                    except Exception as img_err:
                        c.drawString(120, y_position, f"Error loading image: {img_err}")
                        y_position -= 20

                y_position -= 20
                
                if y_position < page_threshold:
                    c.showPage()
                    y_position = 750

        c.showPage()
        c.save()

        pdf_buffer.seek(0)

        return StreamingResponse(
            pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=report_{posted_report_id}.pdf"}
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# @router.get("/api/posted-reports-detail-pdf", summary="특정 보고서 상세 조회(PDF)", description="설비와 회사 이름, 보고서 ID를 기준으로 MinIO에 저장된 특정 보고서를 PDF로 변환하여 조회합니다.")
# async def get_posted_reports_detail_pdf(
#     infra: str, company_name: str, posted_report_id: int, db: AsyncSession = Depends(connect_db)
# ):
#     if not infra:
#         raise HTTPException(
#             status_code=400, detail="Infra name is missing in query parameters"
#         )
#     if not company_name:
#         raise HTTPException(
#             status_code=400, detail="company_name is missing in query parameters"
#         )
#     if not posted_report_id:
#         raise HTTPException(
#             status_code=400, detail="posted_report_id is missing in query parameters"
#         )
    
#     try:
#         file_name = str(posted_report_id) + '_' + infra + "_" + company_name
#         bucket_name = os.environ["MINIO_BUCKET"]
#         response = minio_client.get_object(bucket_name, file_name)

#         data = response.read()
#         response.close()
#         response.release_conn()

#         data_str = data.decode("utf-8")
#         report_data = json.loads(data_str)

#         pdf_buffer = BytesIO()

#         c = canvas.Canvas(pdf_buffer, pagesize=letter)
#         pdfmetrics.registerFont(TTFont("NotoSansKR", "/usr/share/fonts/opentype/noto/NotoSansKR-Medium.ttf"))
#         c.setFont("NotoSansKR", 12)
#         basic_info = [
#             ["Report ID", posted_report_id],
#             ["Infrastructure", infra],
#             ["Company Name", company_name],
#             ["Start Time", report_data.get("start_time", "N/A")],
#             ["End Time", report_data.get("end_time", "N/A")],
#             ["User Name", report_data.get("user_name", "N/A")],
#         ]
#         table = Table(basic_info, colWidths=[2 * inch, 4 * inch])
#         table.setStyle(TableStyle([
#             ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
#             ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
#             ("ALIGN", (0, 0), (-1, -1), "LEFT"),
#             ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
#             ("FONTSIZE", (0, 0), (-1, -1), 10),
#             ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
#             ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
#             ("GRID", (0, 0), (-1, -1), 1, colors.black),
#         ]))
        
#         table.wrapOn(c, 100, 750)
#         table.drawOn(c, 100, 650)
#         y_position = 620
#         page_threshold = 50  # 페이지 전환 임계값

#         inspection_list = report_data.get("inspection_list", [])
#         for i, topic in enumerate(inspection_list):
#             c.setFont("NotoSansKR", 12)
#             c.drawString(100, y_position, f"Topic {i + 1}: {topic['topic']}")
#             y_position -= 20

#             if y_position < page_threshold:
#                 c.showPage()
#                 y_position = 750

#             for instruction in topic["instruction_list"]:
#                 c.setFont("NotoSansKR", 12)
#                 c.drawString(120, y_position, f"Instruction: {instruction['instruction']}")
#                 y_position -= 15
#                 c.drawString(120, y_position, f"Type: {instruction['instruction_type']}")
#                 y_position -= 15
#                 if instruction["options"]:
#                     c.drawString(120, y_position, f"Options: {', '.join(instruction['options'])}")
#                     y_position -= 15
#                 c.drawString(120, y_position, f"Answer: {', '.join(instruction['answer'])}")
#                 y_position -= 50

#                 if instruction["img_url"]:
#                     try:
#                         file_id = int(instruction["img_url"].split("/")[-1])
                        
#                         result = await db.execute(
#                             select(ImgFileModel).where(ImgFileModel.file_id == file_id)
#                         )
#                         image_record = result.scalars().first()
                        
#                         if image_record and image_record.file_data:
#                             image = Image.open(io.BytesIO(image_record.file_data))
#                             image.thumbnail((3 * inch, 2 * inch))  
#                             image_path = f"/tmp/{file_id}.jpg"
#                             image.save(image_path, format="JPEG")

#                             c.drawImage(image_path, 120, y_position - 100, width=3 * inch, height=2 * inch)
#                             y_position -= 120  
#                         else:
#                             c.drawString(120, y_position, "Image not found in database.")
#                             y_position -= 20

#                     except Exception as img_err:
#                         c.drawString(120, y_position, f"Error loading image: {img_err}")
#                         y_position -= 20

#                 y_position -= 20
                
#                 if y_position < page_threshold:
#                     c.showPage()
#                     y_position = 750

#         c.showPage()
#         c.save()

#         pdf_buffer.seek(0)

#         return StreamingResponse(
#             pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=report_{posted_report_id}.pdf"}
#         )

#     except Exception as e:
#         return JSONResponse(content={"error": str(e)}, status_code=500)

# def convert_audio_to_text(audio_file_data, client_id, client_secret):
#     url = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor"
#     headers = {
#         "X-NCP-APIGW-API-KEY-ID": client_id,
#         "X-NCP-APIGW-API-KEY": client_secret,
#         "Content-Type": "application/octet-stream",
#     }

#     response = requests.post(url, headers=headers, data=audio_file_data)

#     if response.status_code == 200:
#         result = response.json()
#         return result.get("text", "")
#     else:
#         raise Exception(f"Failed to convert audio to text: {response.text}")

@router.post("/api/convert-audio-to-text", summary="음성 파일 텍스트 변환(AND)", description="음성 파일을 텍스트로 변환해서 반환합니다."
             ,responses={
                200: {
                    "description": "텍스트 변환 성공.",
                    "content": {
                        "application/json": {
                            "example":{
                                "message": "Audio convert successfully",
                                "text": "안녕하세요. 만나서 반갑습니다.",
                            }
                        }
                    }
                }
            })
async def convert_audio_to_text(file: UploadFile = File(...)):
    try:
        audio_file_data = await file.read()

        url = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor"
        headers = {
            "X-NCP-APIGW-API-KEY-ID": os.environ["NAVER_CLOUD_CLIENT"],
            "X-NCP-APIGW-API-KEY": os.environ["NAVER_CLOUD_SECRET"],
            "Content-Type": "application/octet-stream",
        }

        response = requests.post(url, headers=headers, data=audio_file_data)


        if response.status_code == 200:
            result = response.json()
            result_text = result.get("text", "")
            return JSONResponse(
            content={
                "message": "Audio convert successfully",
                "text": result_text,
            },
            status_code=200
            )
            
        else:
            raise Exception(f"Failed to convert audio to text: {response.text}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# 보고서 등록하기
@router.post("/api/posted-report", summary="보고서 등록(AND)", description="점검 절차에 따른 보고서를 등록하고 MinIO에 저장합니다."
             ,responses={
                200: {
                    "description": "보고서 제출 성공.",
                    "content": {
                        "application/json": {
                            "example":{
                                "message": "Report submitted successfully",
                                "posted_report_id": "제출된 보고서 id"
                            }
                        }
                    }
                }
            })
async def submit_inspected_report(
    data: request_body.InspectedReport, db: AsyncSession = Depends(connect_db)
):
    try:
        start_time = datetime.fromisoformat(data.start_time)
        end_time = datetime.fromisoformat(data.end_time)
        infra_name = data.infra
        company_name = data.company_name
        inspection_list = data.inspection_list
        user_name = data.user_name
        memo = data.memo
        # start_time = datetime.fromisoformat(data['start_time'])
        # end_time = datetime.fromisoformat(data['end_time'])
        # infra_name = data['infra']
        # company_name = data['company_name']
        # user_name = data['user_name']

        # audio_file_data = await file.read()
        # audio_text = convert_audio_to_text(audio_file_data, os.environ["NAVER_CLOUD_CLIENT"], os.environ["NAVER_CLOUD_SECRET"])        

        infra_id_result = await db.execute(
            select(InfraModel.infra_id).where(
                InfraModel.infra_name == infra_name,
                InfraModel.company_name == company_name,
            )
        )
        infra_id = infra_id_result.scalars().first()

        print('infra_id', infra_id)
        if not infra_id:
            raise HTTPException(
                status_code=404,
                detail=f'Infra "{infra_name}" not found for company "{company_name}"',
            )

        report_form_id_result = await db.execute(
            select(ReportFormModel.report_form_id)
            .where(
                ReportFormModel.infra_id == infra_id,
                ReportFormModel.company_name == company_name,
            )
            .order_by(ReportFormModel.last_modified_time.desc())
            .limit(1)
        )
        report_form_id = report_form_id_result.scalars().first()

        print('report_form_id', report_form_id)

        if not report_form_id:
            raise HTTPException(
                status_code=404,
                detail=f'Report form not found for infra "{infra_name}" and company "{company_name}"',
            )

        last_posted_report_count = await db.execute(
            select(func.count(PostedReportModel.posted_report_id))
        )
        last_posted_report_id = last_posted_report_count.scalar()

        bucket_name = os.environ["MINIO_BUCKET"]
        posted_report_path = "/" + bucket_name + "/" + str(last_posted_report_id + 1) + "_" + infra_name + "_" + company_name

        start_time_unix = int(start_time.timestamp())
        end_time_unix = int(end_time.timestamp())

        new_report = PostedReportModel(
            posted_report_path=posted_report_path,
            report_form_id=report_form_id,
            start_time=start_time_unix,
            end_time=end_time_unix,
            company_name=company_name,
            user_name=user_name,
            memo= memo 
        )

        db.add(new_report)
        await db.flush()
        await db.refresh(new_report)

        posted_report_id = new_report.posted_report_id

        data_json = json.dumps(data.dict())
        # data_json = json.dumps(data)
        # file 이름 설정
        file_name = str(posted_report_id) + '_' + infra_name + "_" + company_name

        with io.BytesIO(data_json.encode("utf-8")) as data_file:
            minio_client.put_object(
                bucket_name,
                file_name,
                data_file,
                length=-1,
                part_size=10 * 1024 * 1024,
                content_type="application/json",
            )

        # try:
        #     minio_client.put_object(
        #         bucket_name = os.environ["MINIO_BUCKET_AUDIO"],
        #         object_name = file_name,
        #         data = io.BytesIO(audio_file_data),
        #         length = len(audio_file_data),
        #         content_type = file.content_type
        #     ) 

        # except Exception as e:
        #     raise HTTPException(status_code = 500, detail =f"Error saving file from MinIO: {str(e)}")

        await db.commit()

        return JSONResponse(
            content={
                "message": "Report submitted successfully",
                "posted_report_id": posted_report_id,
            },
            status_code=200,
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.put("/api/posted-report/{posted_report_id}", summary="보고서 수정(AND)", description="기존 보고서를 삭제하고, 새로운 보고서를 등록합니다."
             ,responses={
                200: {
                    "description": "보고서 수정 성공.",
                    "content": {
                        "application/json": {
                            "example":{
                                "message": "Report updated successfully",
                                "posted_report_id": "수정된 보고서 id"
                            }
                        }
                    }
                }
            })
async def update_inspected_report(
    posted_report_id: int,
    data: request_body.InspectedReport, 
    db: AsyncSession = Depends(connect_db)
):
    try:
        # 1. 기존 보고서 삭제 (DB 및 MinIO에서)
        existing_report_result = await db.execute(
            select(PostedReportModel)
            .where(PostedReportModel.posted_report_id == posted_report_id)
        )
        existing_report = existing_report_result.scalars().first()

        if not existing_report:
            raise HTTPException(
                status_code=404,
                detail=f"Report with id {posted_report_id} not found"
            )
        
        # MinIO에서 파일 삭제
        bucket_name = os.environ["MINIO_BUCKET"]
        json_file_name = f"{posted_report_id}.json"
        minio_client.remove_object(bucket_name, json_file_name)

        # DB에서 기존 보고서 삭제
        await db.delete(existing_report)
        await db.flush()

        # 2. 새로운 보고서 등록
        start_time = datetime.fromisoformat(data.start_time)
        end_time = datetime.fromisoformat(data.end_time)
        infra_name = data.infra
        company_name = data.company_name
        inspection_list = data.inspection_list
        user_name = data.user_name
        memo = data.memo

        infra_id_result = await db.execute(
            select(InfraModel.infra_id).where(
                InfraModel.infra_name == infra_name,
                InfraModel.company_name == company_name,
            )
        )
        infra_id = infra_id_result.scalars().first()

        if not infra_id:
            raise HTTPException(
                status_code=404,
                detail=f'Infra "{infra_name}" not found for company "{company_name}"',
            )

        report_form_id_result = await db.execute(
            select(ReportFormModel.report_form_id)
            .where(
                ReportFormModel.infra_id == infra_id,
                ReportFormModel.company_name == company_name,
            )
            .order_by(ReportFormModel.last_modified_time.desc())
            .limit(1)
        )
        report_form_id = report_form_id_result.scalars().first()

        if not report_form_id:
            raise HTTPException(
                status_code=404,
                detail=f'Report form not found for infra "{infra_name}" and company "{company_name}"',
            )

        start_time_unix = int(start_time.timestamp())
        end_time_unix = int(end_time.timestamp())

        # 새로운 보고서 추가
        new_report = PostedReportModel(
            posted_report_path=f"/{bucket_name}/{posted_report_id}",
            report_form_id=report_form_id,
            start_time=start_time_unix,
            end_time=end_time_unix,
            company_name=company_name,
            user_name=user_name,
            memo=memo
        )

        db.add(new_report)
        await db.flush()
        await db.refresh(new_report)

        new_posted_report_id = new_report.posted_report_id

        data_json = json.dumps(data.dict())
        json_file_name = f"{new_posted_report_id}.json"

        # MinIO에 파일 업로드
        with io.BytesIO(data_json.encode("utf-8")) as data_file:
            minio_client.put_object(
                bucket_name,
                json_file_name,
                data_file,
                length=-1,
                part_size=10 * 1024 * 1024,
                content_type="application/json",
            )

        await db.commit()

        return JSONResponse(
            content={
                "message": "Report updated successfully",
                "posted_report_id": new_posted_report_id,
            },
            status_code=200,
        )
    except Exception as e:
        await db.rollback()  # 예외 발생 시 롤백
        return JSONResponse(content={"error": str(e)}, status_code=500)



# 이미지 업로드
@router.post("/api/upload-image", summary="이미지 업로드(AND)", description="이미지 파일을 업로드하고 저장된 파일의 URL을 반환합니다."
             ,responses={
                200: {
                    "description": "이미지 저장 성공.",
                    "content": {
                        "application/json": {
                            "example":{
                                "file_id": "이미지 조회시 사용할 id"
                            }                          
                        }
                    }
                }
            })
async def upload_image_to_minio(file: UploadFile = File(...), db: AsyncSession = Depends(connect_db)):
    try:
        file_name = file.filename
        file_extension = os.path.splitext(file_name)[1].lower()

        if file_extension not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        file_name = os.path.splitext(file_name)[0]
        file_data = file.file.read()

        new_image = ImgFileModel(
            file_name = file_name,
            file_size = len(file_data),
            file_data = file_data
        )
        
        db.add(new_image)
        await db.commit()
        await db.refresh(new_image)

        return JSONResponse(content={"file_id": new_image.file_id}, status_code=200)

    except Exception as e:
        db.rollback()
        return JSONResponse(content={"error": str(e)}, status_code=500)
    

# 이미지 조회
@router.get("/api/images/{file_id}", summary="이미지 조회(AND)", description="저장된 이미지 파일을 조회합니다."
            ,responses={
                200: {
                    "description": "이미지 조회 성공.",
                    "content": {
                        "image/jpeg": {
                            "example":{
                                "body": "이미지 데이터"
                            }                          
                        }
                    }
                }
            })
async def get_image(file_id : int, db: AsyncSession = Depends(connect_db)):
    result = await db.execute(
        select(ImgFileModel).where(ImgFileModel.file_id == file_id)
    )
    
    image = result.scalars().first()  
    
    if not image:
        raise HTTPException(status_code=404, detail="image not found")
    
    return StreamingResponse(BytesIO(image.file_data), media_type="image/jpeg")

# 음성 파일 minio 저장
@router.post("/api/audio/", summary="음성 메모 파일 저장(AND)", description="제출 보고서에 해당하는 음성 메모 파일을 저장합니다."
            ,responses={
                200: {
                    "description": "음성 메모 저장 성공.",
                    "content": {
                        "application/json": {
                            "example":{
                                "message": "Audio submitted successfully",
                                "file_name": "1_infra_company-name"
                            }                          
                        }
                    }
                }
            })
async def submit_audio(
    infra: str,
    company_name: str,
    posted_report_id: int,
    file: UploadFile = File(...)
    ):
    try:        
        bucket_name = os.environ["MINIO_BUCKET_AUDIO"]

        audio_file_data = await file.read()    
        
        file_name = str(posted_report_id) + '_' + infra + "_" + company_name

        try:
            minio_client.put_object(
                bucket_name = bucket_name,
                object_name = file_name,
                data = io.BytesIO(audio_file_data),
                length = len(audio_file_data),
                content_type = file.content_type
            ) 

        except Exception as e:
            raise HTTPException(status_code = 500, detail =f"Error saving file from MinIO: {str(e)}")

        return JSONResponse(
            content={
                "message": "Audio submitted successfully",
                "file_name": file_name
            },
            status_code=200,
        )

        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving media: {str(e)}")


@router.get("/api/audio/", summary="제출 보고서 음성 메모 조회(AND)", description="제출 보고서에 해당하는 음성 메모 파일을 조회합니다."
            ,responses={
                200: {
                    "description": "음성 메모 조회 성공.",
                    "content": {
                        "audio/wav": {
                            "example":{
                                "body": "음성 메모 데이터"
                            }                          
                        }
                    }
                }
            })
async def get_audio(
    infra: str,
    company_name: str,
    posted_report_id: int):

    try:        
        bucket_name = os.environ["MINIO_BUCKET_AUDIO"]
        media_type = "audio/wav"
        
        file_name = str(posted_report_id) + "_" + infra + "_" + company_name
        try:
            file_data = minio_client.get_object(bucket_name, file_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving file from MinIO: {str(e)}")

        encoded_filename = urllib.parse.quote(file_name)

        return StreamingResponse(
            io.BytesIO(file_data.read()), 
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving media: {str(e)}")
