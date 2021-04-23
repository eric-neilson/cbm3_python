import os

FORMATS = [
    "csv", "hdf", "excel", "feather"
]


class CBM3ResultsFileWriter:

    def __init__(self, format, out_path, writer_kwargs):
        if format not in FORMATS:
            raise ValueError(
                f"format must be one of: {FORMATS}")

        self.format = format
        if format == "csv":
            self.out_dir = out_path
        else:
            self.out_dir = os.path.dirname(out_path)
        self.out_path = out_path
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

        self.created_files = set()
        self.writer_kwargs = writer_kwargs

    def _def_get_file_path(self, name):
        if self.format == "csv":
            return os.path.join(self.out_dir, f"{name}.csv")
        else:
            return self.out_path

    def write(self, name, df):
        out_path = self._def_get_file_path(name)
        if out_path not in self.created_files:
            if os.path.exists(out_path):
                os.remove(out_path)
            self.created_files.add(out_path)
        args = [out_path]

        if self.format == "csv":
            kwargs = dict(
                mode='a', index=False,
                header=not os.path.exists(out_path))
            kwargs.update(self.writer_kwargs)
            df.to_csv(*args, **kwargs)
        elif self.format == "hdf":
            kwargs = dict(key=name, mode="a")
            kwargs.update(self.writer_kwargs)
            df.to_hdf(*args, **kwargs)
        elif self.format == "excel":
            kwargs = dict(sheet_name=name, index=False)
            kwargs.update(*args, **kwargs)
            df.to_excel(out_path, )
        elif self.format == "feather":
            kwargs = dict()
            kwargs.update(self.writer_kwargs)
            df.to_feather(*args, **kwargs)