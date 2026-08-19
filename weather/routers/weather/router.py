import csv
from datetime import datetime
from io import BytesIO, StringIO

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather.core.database import get_session
from weather.models.weather.weather_log import WeatherLog
from weather.schemas.weather.weather_city import WeatherCitySchema
from weather.schemas.weather.weather_insight import (
    WeatherInsightRequest,
    WeatherInsightResponse,
    WeatherInsightTaskResponse,
)
from weather.schemas.weather.weather_log import (
    WeatherLogListResponse,
    WeatherLogResponse,
    WeatherLogSortField,
    WeatherLogSortOrder,
)
from weather.schemas.weather.weather_task import (
    WeatherInsightTaskStatusResponse,
    WeatherTaskResponseSchema,
)
from weather.services.weather.insight_service import InsightService
from weather.services.weather.weather_service import WeatherService
from weather.tasks.weather.weather_tasks import (
    collect_current_weather,
    generate_weather_insight,
)

router = APIRouter()


@router.post(
    path='/',
    status_code=status.HTTP_201_CREATED,
    response_model=WeatherTaskResponseSchema,
    summary='Coletar clima de uma cidade',
)
async def weather_city(
    data: WeatherCitySchema,
    db: AsyncSession = Depends(get_session),
):
    task = collect_current_weather.delay(
        data.city,
    )

    return {
        'message': 'Coleta do clima enviada para processamento.',
        'task_id': task.id,
    }


@router.post(
    path='/generate-insight',
    response_model=WeatherInsightTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary='Gerar insight climático',
    description=(
        'Dispara uma tarefa assíncrona para gerar um insight climático '
        'com base nos dados meteorológicos coletados.'
    ),
)
async def generate_insight(
    data: WeatherInsightRequest,
) -> WeatherInsightTaskResponse:
    task = generate_weather_insight.delay(
        hours=data.hours,
        city=data.city,
    )

    return WeatherInsightTaskResponse(
        message='Geração do insight iniciada.',
        task_id=task.id,
        hours=data.hours,
        city=data.city,
    )


@router.get(
    path='/insight-task/{task_id}',
    response_model=WeatherInsightTaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary='Consultar status da geração do insight',
)
async def get_insight_task_status(
    task_id: str,
) -> WeatherInsightTaskStatusResponse:

    task = AsyncResult(
        task_id,
        app=generate_weather_insight.app,
    )

    result = None

    if task.successful():
        result = str(task.result)

    return WeatherInsightTaskStatusResponse(
        task_id=task_id,
        status=task.status,
        result=result,
    )


@router.get(
    path='/insights',
    response_model=list[WeatherInsightResponse],
    status_code=status.HTTP_200_OK,
    summary='Listar insights climáticos',
    description=(
        'Retorna os insights climáticos gerados pela IA, '
        'ordenados do mais recente para o mais antigo.'
    ),
)
async def get_weather_insights(
    db: AsyncSession = Depends(get_session),
) -> list[WeatherInsightResponse]:
    service = WeatherService(db)

    return await service.get_weather_insights()


@router.get(
    path='/',
    status_code=status.HTTP_200_OK,
    response_model=WeatherLogListResponse,
    summary='Listar coletas de clima',
)
async def list_weather(
    city: str | None = Query(
        default=None,
        description='Filtra pelo nome da cidade',
    ),
    temperature_min: float | None = Query(
        default=None,
        description='Temperatura mínima',
    ),
    temperature_max: float | None = Query(
        default=None,
        description='Temperatura máxima',
    ),
    start_date: datetime | None = Query(
        default=None,
        description='Data/hora inicial da coleta',
    ),
    end_date: datetime | None = Query(
        default=None,
        description='Data/hora final da coleta',
    ),
    condition: str | None = Query(
        default=None,
        description='Filtra pela condição climática',
    ),
    sort_by: WeatherLogSortField = Query(
        default='created_at',
        description='Campo utilizado para ordenação',
    ),
    sort_order: WeatherLogSortOrder = Query(
        default='desc',
        description='Direção da ordenação',
    ),
    page: int = Query(
        default=1,
        ge=1,
        description='Número da página',
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
        description='Quantidade de registros por página',
    ),
    db: AsyncSession = Depends(get_session),
):
    query = select(WeatherLog)

    # Filtro por temperatura mínima
    if temperature_min is not None:
        query = query.where(WeatherLog.temperature >= temperature_min)

    # Filtro por temperatura máxima
    if temperature_max is not None:
        query = query.where(WeatherLog.temperature <= temperature_max)

    # Filtro por data inicial
    if start_date is not None:
        query = query.where(WeatherLog.timestamp >= start_date)

    # Filtro por data final
    if end_date is not None:
        query = query.where(WeatherLog.timestamp <= end_date)

    # Filtro por condição climática
    if condition:
        query = query.where(WeatherLog.condition.ilike(f'%{condition}%'))

    # Ordenação
    sort_column = getattr(WeatherLog, sort_by)

    if sort_order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Busca os registros antes da paginação,
    # pois o filtro de cidade será normalizado em Python.
    result = await db.scalars(query)

    weather_logs = result.all()

    # Filtro por cidade ignorando acentos e maiúsculas/minúsculas
    if city:
        normalized_city = InsightService._normalize_city(city)

        weather_logs = [
            weather_log
            for weather_log in weather_logs
            if normalized_city
            in InsightService._normalize_city(weather_log.city)
        ]

    # Total após todos os filtros
    total = len(weather_logs)

    # Paginação
    offset = (page - 1) * page_size

    paginated_weather_logs = weather_logs[offset : offset + page_size]

    total_pages = (total + page_size - 1) // page_size if total else 0

    return {
        'items': paginated_weather_logs,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    }


@router.get(
    path='/export-csv',
    summary='Exportar coletas de clima em CSV',
)
async def export_csv(
    city: str | None = Query(default=None),
    order: str = Query(default='desc', pattern='^(asc|desc)$'),
    db: AsyncSession = Depends(get_session),
):
    service = WeatherService(db)

    logs = await service.get_weather_logs(
        city=city,
        order=order,
    )

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        'id',
        'timestamp',
        'city',
        'temperature',
        'humidity',
        'pressure',
        'wind_speed',
        'condition',
        'created_at',
    ])

    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat(),
            log.city,
            log.temperature,
            log.humidity,
            log.pressure,
            log.wind_speed,
            log.condition,
            log.created_at.isoformat(),
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': ('attachment; filename="weather_logs.csv"')
        },
    )


@router.get(
    path='/export-xlsx',
    summary='Exportar coletas de clima em XLSX',
)
async def export_xlsx(
    city: str | None = Query(default=None),
    order: str = Query(default='desc', pattern='^(asc|desc)$'),
    db: AsyncSession = Depends(get_session),
):
    service = WeatherService(db)

    logs = await service.get_weather_logs(
        city=city,
        order=order,
    )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Weather Logs'

    worksheet.append([
        'ID',
        'Timestamp',
        'Cidade',
        'Temperatura',
        'Umidade',
        'Pressão',
        'Velocidade do vento',
        'Condição',
        'Criado em',
    ])

    for log in logs:
        worksheet.append([
            log.id,
            log.timestamp.isoformat(),
            log.city,
            log.temperature,
            log.humidity,
            log.pressure,
            log.wind_speed,
            log.condition,
            log.created_at.isoformat(),
        ])

    worksheet.freeze_panes = 'A2'
    worksheet.auto_filter.ref = worksheet.dimensions

    column_widths = {
        'A': 10,
        'B': 25,
        'C': 25,
        'D': 15,
        'E': 15,
        'F': 15,
        'G': 20,
        'H': 25,
        'I': 25,
    }

    for column, width in column_widths.items():
        worksheet.column_dimensions[column].width = width

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ),
        headers={
            'Content-Disposition': ('attachment; filename="weather_logs.xlsx"')
        },
    )


@router.get(
    path='/{weather_id}',
    response_model=WeatherLogResponse,
    status_code=status.HTTP_200_OK,
    summary='Buscar coleta de clima por ID',
)
async def get_weather_by_id(
    weather_id: int,
    db: AsyncSession = Depends(get_session),
):
    service = WeatherService(db)

    weather_log = await service.get_weather_log_by_id(weather_id)

    if weather_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Coleta de clima não encontrada.',
        )

    return weather_log


@router.delete(
    path='/{weather_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Excluir coleta de clima por ID',
)
async def delete_weather_by_id(
    weather_id: int,
    db: AsyncSession = Depends(get_session),
):
    service = WeatherService(db)

    deleted = await service.delete_weather_log(weather_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Coleta de clima não encontrada.',
        )
