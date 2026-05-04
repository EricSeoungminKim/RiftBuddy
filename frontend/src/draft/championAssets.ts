export const DDRAGON_VERSION = '16.9.1'

const DDRAGON_BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img/champion`

const CHAMPION_ID_ALIASES: Record<string, string> = {
  Chogath: 'Chogath',
  Drmundo: 'DrMundo',
  Jarvaniv: 'JarvanIV',
  JarvanIV: 'JarvanIV',
  Kaisa: 'Kaisa',
  KaiSa: 'Kaisa',
  KhaZix: 'Khazix',
  Khazix: 'Khazix',
  Kogmaw: 'KogMaw',
  Ksante: 'KSante',
  KSante: 'KSante',
  Leesin: 'LeeSin',
  LeeSin: 'LeeSin',
  Masteryi: 'MasterYi',
  Missfortune: 'MissFortune',
  Monkeyking: 'MonkeyKing',
  Nunu: 'Nunu',
  RekSai: 'RekSai',
  Reksai: 'RekSai',
  Tahmkench: 'TahmKench',
  Twistedfate: 'TwistedFate',
  Xinzhao: 'XinZhao',
  XinZhao: 'XinZhao',
}

export function championAssetId(champion: string): string {
  const cleaned = champion.replace(/[^a-zA-Z0-9]/g, '')
  if (!cleaned) return champion
  const normalized = cleaned.toLowerCase()
  const pascal = normalized[0].toUpperCase() + normalized.slice(1)
  return CHAMPION_ID_ALIASES[pascal] ?? pascal
}

export function championIconUrl(champion: string): string {
  return `${DDRAGON_BASE}/${championAssetId(champion)}.png`
}
