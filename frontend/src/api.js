export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}
export async function api(path, options = {}) {
  const { body, ...rest } = options;
  let response;
  try {
    response = await fetch(`/api${path}`, { ...rest, credentials: 'same-origin', headers: { ...(body !== undefined ? {'Content-Type': 'application/json'} : {}), ...rest.headers }, ...(body !== undefined ? {body: JSON.stringify(body)} : {}) });
  } catch { throw new ApiError('Нет связи с сервером. Проверьте подключение и попробуйте снова.', 0); }
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login' && path !== '/auth/me') window.dispatchEvent(new Event('session-expired'));
    const detail = data?.detail;
    const message = Array.isArray(detail) ? detail.map(item => `${item.loc?.slice(1).join('.') || 'Поле'}: ${item.msg}`).join('; ') : typeof detail === 'string' ? detail : 'Сервер не смог обработать запрос. Попробуйте ещё раз.';
    throw new ApiError(message, response.status);
  }
  return data;
}
export const money = value => new Intl.NumberFormat('ru-RU', {style:'currency',currency:'RUB',maximumFractionDigits:0}).format(Number(value || 0));
// API returns local service time without an offset. Do not convert it through UTC.
export const dateTime = value => value ? new Date(value).toLocaleString('ru-RU',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : '—';
export const time = value => value ? new Date(value).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'}) : '—';
export const today = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
export const labels = {new:'Новая',confirmed:'Подтверждена',in_progress:'В работе',completed:'Завершено',cancelled:'Отменено',no_show:'Неявка'};
