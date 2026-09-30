from pathlib import Path
from pyspark.sql import DataFrame


class ParquetWriter:

    def __init__(self, output_dir: str = "data/curated/npm"):
        self.output_dir = Path(output_dir)

    def write(self, data: dict[str, DataFrame]) -> None:
        """
        Writes each DataFrame in `data` to a Parquet subdirectory under `output_dir`.

        Parameters
        ----------
        data : dict[str, DataFrame]
            Dictionary of dataset name -> Spark DataFrame.
        """
        for name, df in data.items():
            target_path = self.output_dir / name
            print(f"\nWriting dataset '{name}' to {target_path}...")
            df.write.mode("overwrite").parquet(str(target_path))
            print(f"Successfully written '{name}'.")
