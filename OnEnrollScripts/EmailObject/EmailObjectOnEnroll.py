#this OnEnroll script sends the Data object via email

EmailTo = 834
QueuedBy = 834
EmailFromAddress = 'jpierson@fcchudson.com'
EmailFromName = 'TouchPoint Script - JakePierson'
EmailSubject = 'OnEnroll Data object'
person = model.GetPerson(Data.PeopleId)
spouse = model.GetSpouse(Data.PeopleId)

EmailBody1 = '<pre>{0}</pre>'.format(spouse.PeopleId)

model.Email(EmailTo, QueuedBy, EmailFromAddress, EmailFromName, EmailSubject, EmailBody1)
