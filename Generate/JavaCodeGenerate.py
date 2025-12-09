import time

import dotenv
import yaml
from dill import temp
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_deepseek import ChatDeepSeek
import os
from dotenv import load_dotenv
from pathlib import Path
import tempfile

from Generate.file_utils import write_overwrite_atomic, extract_java_code, write_if_not_exists, file_exists


# 读取 YAML 配置文件
def load_config(file_path='config.yaml'):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


# 加载数据库配置
def load_db_config():
    db_config = {
        "host": os.getenv('DB_HOST'),
        "port": int(os.getenv('DB_PORT')),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }
    return db_config


# 获取数据库连接
def define_db_connection():
    try:
        import psycopg2
    except ImportError as e:
        raise ImportError("psycopg2 未安装，请运行: pip install psycopg2-binary") from e
    db_config = load_db_config()
    print(db_config)
    conn = psycopg2.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
    )
    print("数据库连接已建立")
    return conn


# 测试数据库连接
def test_db_connection():
    conn = define_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f"数据库版本: {db_version[0]}")
    cursor.close()
    conn.close()
    print("数据库连接已关闭")


def list_tables(conn, schema='public', prefix=''):
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = %s AND table_type = 'BASE TABLE'
    AND table_name LIKE %s 
    ORDER BY table_name;
    """

    # 调试输出
    print(f"Executing query: {query}")
    print(f"输入参数: (schema: {schema}, prefix: {prefix})")

    with conn.cursor() as cur:
        cur.execute(query, (schema, f'{prefix}%'))  # 执行查询
        rows = cur.fetchall()

    # 输出查询到的表
    tables = [r[0] for r in rows]
    print(f"Found tables: {tables}")
    return tables


def get_columns(conn, table, schema='public'):
    query = """
    SELECT c.column_name, c.data_type, c.is_nullable, 
           c.character_maximum_length, c.numeric_precision, c.numeric_scale,
           CASE WHEN kcu.column_name IS NOT NULL THEN 'PRIMARY KEY' ELSE '' END AS is_primary_key,
           pg_catalog.col_description(attrelid, attnum) AS column_comment
    FROM information_schema.columns c
    LEFT JOIN information_schema.key_column_usage kcu 
        ON kcu.table_schema = c.table_schema
        AND kcu.table_name = c.table_name
        AND kcu.column_name = c.column_name
    LEFT JOIN pg_catalog.pg_attribute a 
        ON a.attrelid = (SELECT oid FROM pg_catalog.pg_class WHERE relname = c.table_name AND relnamespace = (SELECT oid FROM pg_catalog.pg_namespace WHERE nspname = c.table_schema))
        AND a.attname = c.column_name
    WHERE c.table_schema = %s AND c.table_name = %s
    ORDER BY c.ordinal_position;
    """

    with conn.cursor() as cur:
        cur.execute(query, (schema, table))
        cols = cur.fetchall()
    print(f"表 `{table}` 的字段: {cols}")
    return cols


# 生成实体类
def generate_entity_class(table_name, columns, module_name, base_path):
    # 调用AI模型生成实体类代码
    model = ChatDeepSeek(
        model="deepseek-chat",
        api_key=os.getenv("API_KEY"),
    )

    messages = [
        SystemMessage(content="""
        你是一个资深的Java后端开发工程师，精通Java编码规范。
        请根据提供的数据库表结构生成对应的Java实体类代码。
        数据库使用的是PostgreSQL。
        注意事项:
        1. 类名使用大驼峰命名法，字段名使用小驼峰命名法,类名前面要加上Base,格式为BaseTableName。
        2. 根据字段类型选择合适的Java数据类型。
        3. 为每个字段添加注释，说明字段含义。
        4. 包含必要的import语句。
        5. 可以添加Mybatis Plus的注解，如@TableName, @TableId等。
        6. 生成的代码要符合Java编码规范。
        7. 只输出 ``java包裹的代码，且不要任何解释
        8. 包名格式: com.xhn.{module_name}.{table_suffix}.model
        """),
        HumanMessage(
            content=f"请根据以下表结构生成Java实体类代码，模块名是{module_name},表名: {table_name}, 字段: {columns}"
        )
    ]
    response = model.invoke(messages)
    print(f"生成的Java实体类代码:\n{response.content}")
    raw_content = response.content
    java_code = extract_java_code(raw_content)
    # 去掉下划线，变成驼峰命名法
    TableName = ''.join(word.capitalize() for word in table_name.split('_'))
    # 将生成的代码保存到文件

    output_dir_path = base_path / 'model'

    output_dir_path.mkdir(parents=True, exist_ok=True)
    file_path = output_dir_path / f"Base{TableName}.java"
    write_overwrite_atomic(file_path, java_code)
    # with open(file_path, "w", encoding="utf-8") as f:
    #     f.write(java_code)

    file_path = output_dir_path / f"{TableName}.java"
    if (file_exists(file_path)):
        print(f"文件已存在，跳过生成: {file_path}")
        return AIMessage(
            [response.content]
        )
    messages = [
        SystemMessage(content="""
            你是一个资深的Java后端开发工程师，精通Java编码规范。
            根据上一轮生成的实体类为基类，写一个新类。
            注意事项:
            1. 类名使用大驼峰命名法，字段名使用小驼峰命名法。
            2. 包含必要的import语句。
            3. 生成的代码要符合Java编码规范。
            4. 只输出 ``java包裹的代码，且不要任何解释
            5. 包名格式: com.xhn.{module_name}.{table_suffix}.model
            6. 新类继承自Base类,且不要任何字段和方法
            7. 新类类名前面不要加Base
            """),
        AIMessage(
            [response.content]
        ),
        HumanMessage(
            content=f"请根据这个基类生成他的继承类，基类对应表名为 {table_name},其中模块名是{module_name},基类和这个类在同一个包下,生成的类要实现Serializable接口"
        )
    ]
    response = model.invoke(messages)

    write_if_not_exists(file_path, extract_java_code(response.content))
    return AIMessage([response.content])


def generate_dao_class(ai_massage, module_name, table_name, base_path, table_suffix, project_root):
    model = ChatDeepSeek(
        model="deepseek-chat",
        api_key=os.getenv("API_KEY"),
    )
    date = time.time()
    messages = [
        SystemMessage(content="""
           你是一个资深的Java后端开发工程师，精通Java编码规范。
           请根据提供的实体类代码生成MybatisPlus的dao层。
           注意事项:
           1. 类名使用大驼峰命名法，命名格式是{TableName}Mapper。
           4. 包含必要的import语句。
           5. 继承自BaseMapper<{TableName}>。
           6. 生成的代码要符合Java编码规范。
           7. 只输出 ``java包裹的代码，且不要任何解释
           8. 包名格式: com.xhn.{module_name}.{table_suffix}.mapper,实体类代码在com.xhn.{module_name}.{table_suffix}.model包下
           """),
        HumanMessage(
            content=f"根据信息生成基本的mapper层代码，模块名是{module_name},"
                    f"表名: {table_name},table_suffix是{''.join(table_name.split('_')[1:])},"
                    f"注释加上@author xhn 和 @date 当前时间戳是 {date}"
        ),
        ai_massage
    ]
    response = model.invoke(messages)
    output_dir_path = base_path / 'mapper'
    output_dir_path.mkdir(parents=True, exist_ok=True)
    TableName = ''.join(word.capitalize() for word in table_name.split('_'))
    file_path = output_dir_path / f"{TableName}Mapper.java"
    write_if_not_exists(file_path, extract_java_code(response.content))
    # 写入mapper对应的xml文件
    xml_output_dir_path = Path(project_root) / 'src' / 'main' / 'resources' / 'mapper' / module_name

    xml_output_dir_path.mkdir(parents=True, exist_ok=True)
    file_path = xml_output_dir_path / f"{TableName}Mapper.xml"
    if file_exists(file_path):
        print(f"文件已存在，跳过生成: {file_path}")
        return AIMessage(
            [response.content]
        )
    xml_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd" >
<mapper namespace="com.xhn.{module_name}.{table_suffix}.mapper.{TableName}Mapper">
    
</mapper>
    """
    write_if_not_exists(file_path, xml_content)

    return AIMessage([response.content])


def generate_service_class(ai_massage, module_name, table_name, base_path, table_suffix, project_root):
    interface_dir_path = base_path / 'service'
    interface_dir_path.mkdir(parents=True, exist_ok=True)
    TableName = ''.join(word.capitalize() for word in table_name.split('_'))
    model = ChatDeepSeek(
        model="deepseek-chat",
        api_key=os.getenv("API_KEY"),
    )
    date = time.time()
    if file_exists(interface_dir_path / f"{TableName}Service.java"):
        print(f"文件已存在，跳过生成: {interface_dir_path / f'{TableName}Service.java'}")
    else:
        messages = [
            SystemMessage(content="""
                  你是一个资深的Java后端开发工程师，精通Java编码规范。
                  请生成service接口层代码,框架集成了MybatisPlus。
                  注意事项:
                  1. 接口名使用大驼峰命名法，命名格式是{TableName}Service。
                  2. 包含必要的import语句。
                  3. 继承自IService<{TableName}>。
                  4. 生成的代码要符合Java编码规范。
                  5. 只输出 ``java包裹的代码，且不要任何解释
                  6. 包名格式: com.xhn.{module_name}.{table_suffix}.service,实体类代码在com.xhn.{module_name}.{table_suffix}.model包下。
                  """),
            HumanMessage(
                content=f"请根据信息生成基本的Service接口，模块名是{module_name},"
                        f"表名: {table_name},table_suffix是{''.join(table_name.split('_')[1:])},"
                        f"注释加上@author xhn 和 @date 当前时间戳是 {date}"
            )
        ]
        response = model.invoke(messages)
        file_path = interface_dir_path / f"{TableName}Service.java"
        write_if_not_exists(file_path, extract_java_code(response.content))
    impl_dir_path = base_path / 'service' / 'impl'
    impl_dir_path.mkdir(parents=True, exist_ok=True)
    if file_exists(impl_dir_path / f"{TableName}ServiceImpl.java"):
        print(f"文件已存在，跳过生成: {impl_dir_path / f'{TableName}ServiceImpl.java'}")
    else:

        messages = [
            SystemMessage(content="""
                      你是一个资深的Java后端开发工程师，精通Java编码规范。
                      请生成service实现类代码,框架集成了MybatisPlus。
                      注意事项:
                      1. 类名使用大驼峰命名法，命名格式是{TableName}ServiceImpl。
                      2. 包含必要的import语句。
                      3. 继承自ServiceImpl<{TableName}Mapper, {TableName}>并实现{TableName}Service接口。
                      4. 生成的代码要符合Java编码规范。
                      5. 只输出 ``java包裹的代码，且不要任何解释
                      6. 包名格式: com.xhn.{module_name}.{table_suffix}.service.impl,
                      实体类代码在com.xhn.{module_name}.{table_suffix}.model包下,
                      mapper在com.xhn.{module_name}.{table_suffix}.mapper包下
                      接口代码在com.xhn.{module_name}.{table_suffix}.service下。
                      7. 代码要加上不要的注释
                      8. 类上要加上@Service注解
                      """),
            HumanMessage(
                content=f"请根据信息生成基本的Service实现类，"
                        f"模块名是{module_name},表名: {table_name},table_suffix是{''.join(table_name.split('_')[1:])},"
                        f"注释加上@author xhn 和 @date 当前时间戳是 {date}"
            ),
            ai_massage
        ]
        response = model.invoke(messages)
        file_path = impl_dir_path / f"{TableName}ServiceImpl.java"
        write_if_not_exists(file_path, extract_java_code(response.content))


def generate_controller_class(ai_massage, module_name, table_name, base_path, table_suffix, project_root):
    interface_dir_path = base_path / 'controller'
    interface_dir_path.mkdir(parents=True, exist_ok=True)
    TableName = ''.join(word.capitalize() for word in table_name.split('_'))
    if file_exists(interface_dir_path / f"{TableName}Controller.java"):
        print(f"文件已存在，跳过生成: {interface_dir_path / f'{TableName}Controller.java'}")
        return
    model = ChatDeepSeek(
        model="deepseek-chat",
        api_key=os.getenv("API_KEY"),
    )
    date = time.time()
    messages = [
        SystemMessage(content=f"""
              你是一个资深的Java后端开发工程师，精通Java编码规范。
              请生成Controller层代码,框架集成了MybatisPlus。
              注意事项:
              1. 类名使用大驼峰命名法，命名格式是{TableName}Controller。
              2. 包含必要的import语句。
              3. 生成的代码要符合Java编码规范。
              4. 只输出 ``java包裹的代码，且不要任何解释
              5. 包名格式: com.xhn.{module_name}.{table_suffix}.controller,
              实体类代码在com.xhn.{module_name}.{table_suffix}.model包下。
              6. 类上要加上@RestController和@RequestMapping注解，RequestMapping的路径格式是 /{module_name}/{table_suffix}
              """),
        HumanMessage(
            content=f"请根据信息生成基本的Controller类，模块名是{module_name},"
                    f"表名: {table_name},table_suffix是{''.join(table_name.split('_')[1:])},"
                    f"使用@Autowired注解注入Service层，在com.xhn.{module_name}.{table_suffix}.service包下，类名是{TableName}Service"
                    f"完成基本的CRUD接口，使用Restful风格。"
                    f"注释加上@author xhn 和 @date 当前时间戳是 {date}"
        )
    ]
    response = model.invoke(messages)
    file_path = interface_dir_path / f"{TableName}Controller.java"
    write_if_not_exists(file_path, extract_java_code(response.content))


def generate_code_for_tables(conn, tables):
    # 生成路径
    project_root = config['project_root']
    # table_name下划线后边部分
    module_name = config['module_name']

    for table in tables:
        table_suffix = ''.join(table.split('_')[1:])
        base_path = Path(project_root) / 'src' / 'main' / 'java' / 'com' / 'xhn' / module_name / table_suffix
        columns = get_columns(conn, table)
        ai_message = generate_entity_class(table, columns, module_name, base_path)
        generate_dao_class(ai_message, module_name, table, base_path, table_suffix, project_root)
        generate_service_class(ai_message, module_name, table, base_path, table_suffix, project_root)
        generate_controller_class(ai_message, module_name, table, base_path, table_suffix, project_root)
        print(f'表{table}生成完成')


if __name__ == '__main__':
    dotenv.load_dotenv()
    conn = define_db_connection()
    config = load_config()

    try:
        list_table = list_tables(conn, 'public', prefix=config['module_name'])
        generate_code_for_tables(conn, list_table)
    finally:
        conn.close()
