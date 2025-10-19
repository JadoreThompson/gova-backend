import dayjs from "dayjs";

export const formatDate = (value: string) => dayjs(value).format("YYYY-MM-DD HH:mm");
