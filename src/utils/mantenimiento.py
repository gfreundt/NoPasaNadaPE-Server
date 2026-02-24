import logging

logger = logging.getLogger(__name__)


def cada_hora(db):
    try:
        cursor, conn = db.cursor(), db.conn

        # Toma datos de SUNARP sobre año de fabricacion y pone el dato en InfoPlacas si esta vacio
        cmd = """ UPDATE InfoPlacas
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

        cursor.execute(cmd)
        conn.commit()

        logger.info("[MANTENIMIENTO HORARIO] Actualizacion AnoFabricacion completa.")

    except Exception as e:
        logger.error(f"Error en mantenimiento de cada hora: {e}")


def cada_dia(db):
    try:
        cursor, conn = db.cursor(), db.conn

        # Pone el valor de IdMember en 0 para placas que no tienen un registro correspondiente en InfoMiembros
        cmd = """
                    UPDATE InfoPlacas
                    SET IdMember_FK = 0
                    WHERE IdMember_FK IS NOT NULL 
                        AND IdMember_FK != 0 
                        AND IdMember_FK NOT IN (SELECT IdMember FROM InfoMiembros)
                """
        cursor.execute(cmd)
        conn.commit()

        logger.info("[MANTENIMIENTO DIARIO] Control de placas huerfanas completa.")

    except Exception as e:
        logger.error(f"Error en mantenimiento de cada dia: {e}")
