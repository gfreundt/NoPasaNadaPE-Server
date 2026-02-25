import logging

from src.updates import datos_actualizar, extrae_data_terceros
from src.utils.utils import calcula_primera_revtec


logger = logging.getLogger(__name__)


def cada_hora(db):
    """Scripts que se ejecutaran todas las horas"""

    try:
        actualiza_ano_de_fabricacion_de_ficha_sunarp(db)
        elimina_revtec_calculada_placas_sin_miembro(db)

    except Exception as e:
        logger.error(f"Error en mantenimiento de cada hora: {e}")

    finally:
        db.conn.commit()


def cada_dia(db):
    """Scripts que se ejecutaran una vez al dia"""

    try:
        recalcula_fechahasta_revtec_de_tabla(db)
        control_placas_huerfanas(db)
        actualiza_datos_nunca_actualizados(db)

    except Exception as e:
        logger.error(f"Error en mantenimiento de cada dia: {e}")

    finally:
        db.conn.commit()


def control_placas_huerfanas(db):
    """
    Modifica el IdMember_FK = 0 para todas las placas que no tienen un miembro asociado
    """

    cmd = """
                UPDATE InfoPlacas
                SET IdMember_FK = 0
                WHERE IdMember_FK IS NOT NULL 
                    AND IdMember_FK != 0 
                    AND IdMember_FK NOT IN (SELECT IdMember FROM InfoMiembros)
            """

    cursor = db.cursor()
    cursor.execute(cmd)

    logger.info(
        f"[MANTENIMIENTO DIARIO] Control de placas huerfanas completa. Regsitros modificados: {cursor.rowcount}"
    )


def actualiza_ano_de_fabricacion_de_ficha_sunarp(db):
    """
    Actualiza el campo AnoFabricacion en InfoPlacas con el valor del campo Ano de DataSunarpFichas
    para aquellas placas que no tienen un valor previo de AnoFabricacion pero si tienen un valor en DataSunarpFichas
    """

    cmd = """   UPDATE InfoPlacas
                SET AnoFabricacion = (
                    SELECT Ano
                    FROM DataSunarpFichas
                    WHERE DataSunarpFichas.PlacaValidate = InfoPlacas.Placa
                    AND DataSunarpFichas.Ano IS NOT NULL
                    AND DataSunarpFichas.Ano <> ''
                )
                WHERE AnoFabricacion IS NULL
                AND EXISTS (
                    SELECT 1
                    FROM DataSunarpFichas
                    WHERE DataSunarpFichas.PlacaValidate = InfoPlacas.Placa
                        AND DataSunarpFichas.Ano IS NOT NULL
                        AND DataSunarpFichas.Ano <> ''
                );
            """

    cursor = db.cursor()
    cursor.execute(cmd)

    logger.info(
        f"[MANTENIMIENTO HORARIO] Actualizacion AnoFabricacion de fichas SUNARP. Regsitros modificados: {cursor.rowcount}"
    )


def elimina_revtec_calculada_placas_sin_miembro(db):
    """
    Si encuentra un placa que no tiene asociado un miembro, elimina el valor de FechaHasta para esa placa
    si la fecha fue calculada y no obtenida de la pagina web del MTC
    """

    cmd = """ 
            UPDATE DataMtcRevisionesTecnicas
                SET FechaHasta = NULL, FechaHastaFueCalculada = 0
                WHERE PlacaValidate IN
                    (SELECT Placa FROM InfoPlacas WHERE IdMember_FK = 0)
			    	AND FechaHastaFueCalculada = 1
            """

    cursor = db.cursor()
    cursor.execute(cmd)

    logger.info(
        f"[MANTENIMIENTO HORARIO] Eliminacion de FechaHasta calculada en placas huerfanas. Registros modificados: {cursor.rowcount}"
    )


def recalcula_fechahasta_revtec_de_tabla(db):
    """
    Revisa todas las placas de la tabla DataMtcRevisionesTecnicas y recalcula la FechaHasta en caso se cumpla lo
    siguiente:  hay un año de fabricacion asociado a la placa,
                no se ha extraido la FechaHasta del MTC previamente,
                esta con flag calculada o FechaHasta esta vacia
    """

    conn = db.connection()
    conn.create_function("CPR", 2, calcula_primera_revtec)
    cmd = """
            UPDATE DataMtcRevisionesTecnicas
            SET
                FechaHasta = CPR(
                                PlacaValidate,
                                (SELECT ip.AnoFabricacion
                                    FROM InfoPlacas ip
                                    WHERE ip.Placa = PlacaValidate
                                    AND ip.AnoFabricacion IS NOT NULL
                                    LIMIT 1)
                                ),
                             FechaHastaFueCalculada = 1

            WHERE
                
                -- debe tener AnoFabricacion
                EXISTS (
                    SELECT 1
                    FROM InfoPlacas ip
                    WHERE ip.Placa = PlacaValidate
                      AND ip.AnoFabricacion IS NOT NULL
                )

                AND
                
                -- saltarse FechaHasta extraido 
                NOT (
                    FechaHasta IS NOT NULL
                    AND (FechaHastaFueCalculada = 0 OR FechaHastaFueCalculada IS NULL)
                )
                
                AND
                
                -- flag calculada o FechaHasta vacia
                (
                    FechaHasta IS NULL
                    OR FechaHastaFueCalculada = 1
                )
            """

    cursor = db.cursor()
    cursor.execute(cmd)
    db.conn.commit()

    logger.info(
        f"[MANTENIMIENTO DIARIO] Recalculo de FechaHasta de DataMtcRevisionesTecnicas. Registros modificados: {cursor.rowcount}"
    )


def actualiza_datos_nunca_actualizados(db):
    """
    Busca todos los datos en InfoMiembros e InfoPlacas que nunca han sido actualizados (fecha default)
    y los manda a actualizar
    """

    pendientes = datos_actualizar.get_datos_nunca_actualizados(db)
    extrae_data_terceros.main(db, pendientes)

    logger.info(
        "[MANTENIMIENTO DIARIO] Actualizando Datos Nunca Actualizados (LastUpdate = '2020-01-01')"
    )
