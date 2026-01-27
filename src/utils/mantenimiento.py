import logging

logger = logging.getLogger(__name__)


def cada_hora(self):
    try:
        cursor, conn = self.db.cursor(), self.cd.conn

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

        logger.info("Mantenimiento cada hora: Actualizacion AnoFabricacion completa.")

    except Exception as e:
        logger.error(f"Error en mantenimiento.cada_hora: {e}")
